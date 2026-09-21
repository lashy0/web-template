"""Users resource routes follow the production permission policy.

Authorization mechanics (401/403, cumulative guards, policy isolation) live in
``tests/unit/lib/authorization``. These tests only verify that the real
production application wires that mechanism onto the users endpoints: the
guards are present, the admin namespace is gone, and the API contract is
stable. No services or databases are stubbed because guards run before
dependency resolution.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from litestar.enums import ScopeType
from litestar.middleware import ASGIMiddleware
from litestar.testing import AsyncTestClient
from litestar.types import ASGIApp, Receive, Scope, Send

from app.db import models as m
from app.db.enums import UserRole
from app.lib.authorization import PermissionPolicy
from app.lib.authorization.guards import AUTHORIZATION_POLICY_STATE_KEY
from app.server.asgi import create_app

pytestmark = [pytest.mark.unit, pytest.mark.auth, pytest.mark.security]

# Requests to the real application must match the route pattern, so they carry
# a valid UUID. The guard denies before the handler runs, so the ID never has
# to resolve to an actual record.
_USER_ID = "00000000-0000-0000-0000-000000000001"

USER_OPERATIONS = (
    ("get", "/users"),
    ("get", f"/users/{_USER_ID}"),
    ("post", "/users"),
    ("patch", f"/users/{_USER_ID}"),
    ("delete", f"/users/{_USER_ID}"),
    ("put", f"/users/{_USER_ID}/password"),
    ("put", f"/users/{_USER_ID}/active"),
    ("put", f"/users/{_USER_ID}/archived"),
)

DENIED_ROLES = (UserRole.MANAGER, UserRole.ENGINEER, UserRole.PACKER, UserRole.OPERATOR)


def test_production_app_installs_immutable_authorization_policy() -> None:
    app = create_app()

    policy = app.state[AUTHORIZATION_POLICY_STATE_KEY]
    assert isinstance(policy, PermissionPolicy)
    assert policy.permissions_for_role(UserRole.ADMINISTRATOR) == frozenset(
        {
            "users.read",
            "users.create",
            "users.update",
            "users.delete",
        }
    )


def test_users_resource_is_registered_once_without_legacy_paths() -> None:
    app = create_app()
    paths = app.openapi_schema.to_schema()["paths"]

    assert not any(path.startswith("/admin/users") for path in paths)

    operation_ids = [
        operation["operationId"]
        for path_item in paths.values()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "patch", "delete", "head", "options"}
    ]
    assert len(operation_ids) == len(set(operation_ids))


def _principal(role: UserRole) -> m.User:
    return m.User(
        identity_id=uuid4(),
        identity_login="http-user",
        name="HTTP User",
        role=role,
    )


class _PrincipalMiddleware(ASGIMiddleware):
    """Inject a trusted principal without touching the app's dependencies."""

    scopes = (ScopeType.HTTP,)

    def __init__(self, user: m.User, litestar_app: Any) -> None:
        self.user = user
        self.litestar_app = litestar_app

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        scope_dict = cast("dict[str, object]", scope)
        scope_dict["user"] = self.user
        scope_dict["litestar_app"] = self.litestar_app
        await next_app(cast("Scope", scope_dict), receive, send)


@pytest.mark.anyio
@pytest.mark.parametrize(("method", "path"), USER_OPERATIONS)
async def test_user_operations_return_401_without_authentication(method: str, path: str) -> None:
    app = create_app()

    async with AsyncTestClient(app) as client:
        response = await getattr(client, method)(path)

    assert response.status_code == 401


@pytest.mark.anyio
@pytest.mark.parametrize(("method", "path"), USER_OPERATIONS)
@pytest.mark.parametrize("role", DENIED_ROLES)
async def test_user_operations_return_403_without_permission(method: str, path: str, role: UserRole) -> None:
    app = create_app()
    asgi_app = _PrincipalMiddleware(user=_principal(role), litestar_app=app)(app.asgi_handler)

    transport = ASGITransport(app=cast("Any", asgi_app))
    async with AsyncClient(transport=transport, base_url="http://testserver.local") as client:
        response = await getattr(client, method)(path)

    assert response.status_code == 403


@pytest.mark.anyio
async def test_head_and_cors_preflight_are_not_blocked_by_permission_guard() -> None:
    app = create_app()

    async with AsyncTestClient(app) as client:
        head_response = await client.head("/users")
        options_response = await client.options(
            "/users",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert head_response.status_code == 405
    assert options_response.status_code in {200, 204}
