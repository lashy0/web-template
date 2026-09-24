from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
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


def _middleware(user: m.User | None) -> KratosAuthenticationMiddleware:
    verifier = AsyncMock()
    verifier.verify_session.return_value = KratosIdentity(id=uuid4(), login="auth-user", is_active=True)
    session = AsyncMock()
    session.scalar.return_value = user
    session_factory = MagicMock()
    session_factory.return_value.__aenter__.return_value = session

    return KratosAuthenticationMiddleware(
        verifier=verifier,
        session_cookie="ory_kratos_session",
        session_factory=session_factory,
    )


async def test_authenticated_session_places_user_in_scope() -> None:
    user = m.User(
        identity_id=uuid4(),
        identity_login="auth-user",
        identity_active=True,
        name="Auth User",
        role=UserRole.OPERATOR,
    )
    scope: dict[str, Any] = {"type": "http", "headers": _COOKIE}
    next_app = AsyncMock()

    await _middleware(user).handle(scope, AsyncMock(), AsyncMock(), next_app)  # type: ignore[arg-type]

    assert scope["user"] is user
    next_app.assert_awaited_once()


async def test_missing_session_cookie_is_unauthorized() -> None:
    with pytest.raises(NotAuthorizedException):
        await _middleware(None).handle({"type": "http", "headers": []}, AsyncMock(), AsyncMock(), AsyncMock())  # type: ignore[arg-type]


async def test_unknown_local_user_is_unauthorized() -> None:
    with pytest.raises(NotAuthorizedException):
        await _middleware(None).handle({"type": "http", "headers": _COOKIE}, AsyncMock(), AsyncMock(), AsyncMock())  # type: ignore[arg-type]


async def test_documentation_is_public() -> None:
    async with AsyncTestClient(create_app()) as client:
        response = await client.get("/schema/openapi.json")

    assert response.status_code == 200


async def test_cors_preflight_is_not_blocked_by_authentication() -> None:
    headers = {"Origin": "http://example.com", "Access-Control-Request-Method": "GET"}

    async with AsyncTestClient(create_app()) as client:
        response = await client.options("/users", headers=headers)

    assert response.status_code in {200, 204}
