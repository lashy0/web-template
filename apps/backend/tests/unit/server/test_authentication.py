from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.testing import AsyncTestClient

from app.db import models as m
from app.db.enums import UserRole
from app.lib.kratos.schemas import KratosIdentity
from app.server.asgi import create_app
from app.server.authentication import KratosAuthenticationMiddleware

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.unit,
    pytest.mark.auth,
]

_COOKIE = [(b"cookie", b"ory_kratos_session=session-value")]
_IDENTITY = KratosIdentity(id=uuid4(), login="auth-user", is_active=True)


def _connection(headers: list[tuple[bytes, bytes]]) -> ASGIConnection[Any, Any, Any, Any]:
    return ASGIConnection({"type": "http", "headers": headers, "state": {}})  # type: ignore[arg-type]


def _middleware(user: m.User | None) -> KratosAuthenticationMiddleware:
    verifier = AsyncMock()
    verifier.verify_session.return_value = _IDENTITY
    session = AsyncMock()
    session.scalar.return_value = user
    session_factory = MagicMock()
    session_factory.return_value.__aenter__.return_value = session

    return KratosAuthenticationMiddleware(
        AsyncMock(),
        verifier=verifier,
        session_cookie="ory_kratos_session",
        session_factory=session_factory,
    )


async def test_authenticated_session_resolves_the_local_user() -> None:
    user = m.User(
        identity_id=uuid4(),
        identity_login="auth-user",
        identity_active=True,
        name="Auth User",
        role=UserRole.OPERATOR,
    )

    result = await _middleware(user).authenticate_request(_connection(_COOKIE))

    assert (result.user, result.auth) == (user, _IDENTITY)


async def test_missing_session_cookie_is_unauthorized() -> None:
    with pytest.raises(NotAuthorizedException):
        await _middleware(None).authenticate_request(_connection([]))


async def test_unknown_local_user_is_unauthorized() -> None:
    with pytest.raises(NotAuthorizedException):
        await _middleware(None).authenticate_request(_connection(_COOKIE))


async def test_documentation_is_public() -> None:
    async with AsyncTestClient(create_app()) as client:
        response = await client.get("/api/schema/openapi.json")

    assert response.status_code == 200


async def test_cors_preflight_is_not_blocked_by_authentication() -> None:
    headers = {"Origin": "http://example.com", "Access-Control-Request-Method": "GET"}

    async with AsyncTestClient(create_app()) as client:
        response = await client.options("/api/users", headers=headers)

    assert response.status_code in {200, 204}
