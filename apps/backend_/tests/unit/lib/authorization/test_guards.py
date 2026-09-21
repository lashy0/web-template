from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from litestar import Litestar, get
from litestar.connection import ASGIConnection
from litestar.datastructures import State
from litestar.enums import ScopeType
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.handlers.base import BaseRouteHandler
from litestar.middleware import ASGIMiddleware
from litestar.testing import AsyncTestClient
from litestar.types import ASGIApp, Receive, Scope, Send

from app.db import models as m
from app.db.enums import UserRole
from app.domain.accounts.permissions import UserPermission
from app.lib.authorization import PermissionPolicy, requires_permission
from app.lib.authorization.guards import AUTHORIZATION_POLICY_STATE_KEY
from app.server.authorization import create_authorization_policy

pytestmark = [pytest.mark.unit, pytest.mark.auth, pytest.mark.security]


def _user(role: UserRole) -> m.User:
    return m.User(
        identity_id=uuid4(),
        identity_login="guard-user",
        name="Guard User",
        role=role,
    )


def _connection(
    user: object = None,
    policy: PermissionPolicy | object | None = None,
) -> Any:
    scope: dict[str, object] = {}
    if user is not None:
        scope["user"] = user
    state: dict[str, object] = {}
    if policy is not None:
        state[AUTHORIZATION_POLICY_STATE_KEY] = policy
    return SimpleNamespace(scope=scope, app=SimpleNamespace(state=state))


def _handler() -> BaseRouteHandler:
    return cast("BaseRouteHandler", SimpleNamespace())


def test_required_permission_allows_authorized_user() -> None:
    requires_permission(UserPermission.READ)(
        _connection(_user(UserRole.ADMINISTRATOR), create_authorization_policy()),
        _handler(),
    )


def test_missing_user_is_unauthorized() -> None:
    with pytest.raises(NotAuthorizedException, match="Authentication required"):
        requires_permission(UserPermission.READ)(_connection(), _handler())


@pytest.mark.parametrize("invalid_user", [None, object(), {"role": UserRole.ADMINISTRATOR}])
def test_invalid_user_is_unauthorized(invalid_user: object) -> None:
    connection = _connection(invalid_user, create_authorization_policy())

    with pytest.raises(NotAuthorizedException, match="Authentication required"):
        requires_permission(UserPermission.READ)(connection, _handler())


def test_missing_permission_is_forbidden() -> None:
    with pytest.raises(PermissionDeniedException, match=r"users\.read"):
        requires_permission(UserPermission.READ)(
            _connection(_user(UserRole.OPERATOR), create_authorization_policy()),
            _handler(),
        )


def test_client_claims_do_not_change_policy() -> None:
    connection = _connection(_user(UserRole.OPERATOR), create_authorization_policy())
    connection.headers = {"x-role": "administrator", "x-permission": "users.read"}

    with pytest.raises(PermissionDeniedException):
        requires_permission(UserPermission.READ)(connection, _handler())


def test_missing_policy_denies_valid_user() -> None:
    with pytest.raises(PermissionDeniedException):
        requires_permission(UserPermission.READ)(_connection(_user(UserRole.ADMINISTRATOR)), _handler())


def test_invalid_policy_type_is_not_treated_as_an_empty_or_admin_policy() -> None:
    with pytest.raises(TypeError, match="PermissionPolicy"):
        requires_permission(UserPermission.READ)(
            _connection(_user(UserRole.ADMINISTRATOR), {UserRole.ADMINISTRATOR: {UserPermission.READ}}),
            _handler(),
        )


def test_policy_changes_apply_to_existing_guard() -> None:
    """Changing one application's grants does not require rebuilding guards."""
    guard = requires_permission(UserPermission.READ)
    app = SimpleNamespace(state={AUTHORIZATION_POLICY_STATE_KEY: create_authorization_policy()})
    connection = cast(
        "ASGIConnection[Any, m.User, Any, Any]",
        SimpleNamespace(scope={"user": _user(UserRole.MANAGER)}, app=app),
    )

    with pytest.raises(PermissionDeniedException):
        guard(connection, _handler())

    app.state[AUTHORIZATION_POLICY_STATE_KEY] = PermissionPolicy({UserRole.MANAGER: {UserPermission.READ}})
    guard(connection, _handler())


class _InjectUserMiddleware(ASGIMiddleware):
    """Test-only trusted principal injector."""

    scopes = (ScopeType.HTTP,)

    def __init__(self, user: m.User) -> None:
        self.user = user

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        scope_dict = cast("dict[str, object]", scope)
        scope_dict["user"] = self.user
        await next_app(cast("Scope", scope_dict), receive, send)


@pytest.mark.anyio
async def test_composed_guard_denies_without_side_effects() -> None:
    calls: list[str] = []

    @get(
        path="/protected",
        guards=[
            requires_permission(UserPermission.READ),
            requires_permission(UserPermission.UPDATE),
        ],
    )
    async def protected() -> dict[str, str]:
        calls.append("protected")
        return {"status": "ok"}

    app = Litestar(
        route_handlers=[protected],
        middleware=[_InjectUserMiddleware(user=_user(UserRole.OPERATOR))],
        state=State({AUTHORIZATION_POLICY_STATE_KEY: create_authorization_policy()}),
    )

    async with AsyncTestClient(app) as client:
        response = await client.get("/protected", headers={"x-permission": "users.update"})

    assert response.status_code == 403
    assert calls == []


@pytest.mark.anyio
async def test_missing_authentication_context_is_401_over_http() -> None:
    calls: list[str] = []

    @get(path="/protected", guards=[requires_permission(UserPermission.READ)])
    async def protected() -> dict[str, str]:
        calls.append("protected")
        return {"status": "ok"}

    app = Litestar(
        route_handlers=[protected],
        state=State({AUTHORIZATION_POLICY_STATE_KEY: create_authorization_policy()}),
    )

    async with AsyncTestClient(app) as client:
        response = await client.get("/protected")

    assert response.status_code == 401
    assert calls == []
