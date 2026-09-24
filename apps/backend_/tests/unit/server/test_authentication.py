from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest
from litestar.exceptions import NotAuthorizedException

from app.db import models as m
from app.db.enums import UserRole
from app.lib.kratos.schemas import KratosIdentity
from app.server.authentication import KratosAuthenticationMiddleware

pytestmark = [pytest.mark.anyio, pytest.mark.unit]


class _Verifier:
    def __init__(self, identity: KratosIdentity) -> None:
        self.identity = identity

    async def verify_session(self, *, cookie_header: str) -> KratosIdentity:
        assert cookie_header == "ory_kratos_session=session-value"
        return self.identity


class _Session:
    def __init__(self, user: m.User | None) -> None:
        self.user = user

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def scalar(self, _statement: Any) -> m.User | None:
        return self.user


def _user(*, active: bool = True, archived: bool = False) -> m.User:
    return m.User(
        identity_id=uuid4(),
        identity_login="auth-user",
        identity_active=active,
        name="Auth User",
        role=UserRole.ADMINISTRATOR,
        archived_at=None if not archived else datetime.now(UTC),
    )


def _middleware(user: m.User | None) -> KratosAuthenticationMiddleware:
    identity_id = user.identity_id if user is not None else uuid4()
    session = _Session(user)

    @asynccontextmanager
    async def session_factory() -> AsyncIterator[_Session]:
        yield session

    return KratosAuthenticationMiddleware(
        verifier=cast(Any, _Verifier(KratosIdentity(identity_id, "auth-user", True))),
        session_cookie="ory_kratos_session",
        session_factory=cast(Any, session_factory),
    )


async def _next_app(scope: Any, receive: Any, send: Any) -> None:
    scope["handled"] = True


async def test_authenticated_session_places_local_user_in_scope() -> None:
    user = _user()
    scope = {"type": "http", "headers": [(b"cookie", b"ory_kratos_session=session-value")]}

    await _middleware(user).handle(scope, cast(Any, None), cast(Any, None), _next_app)

    assert scope["user"] is user
    assert scope["handled"] is True


async def test_missing_session_cookie_is_unauthorized() -> None:
    with pytest.raises(NotAuthorizedException):
        await _middleware(_user()).handle(
            {"type": "http", "headers": []},
            cast(Any, None),
            cast(Any, None),
            _next_app,
        )


@pytest.mark.parametrize("user", [_user(active=False), _user(archived=True)])
async def test_inactive_or_archived_local_user_is_unauthorized(user: m.User) -> None:
    with pytest.raises(NotAuthorizedException):
        await _middleware(user).handle(
            {"type": "http", "headers": [(b"cookie", b"ory_kratos_session=session-value")]},
            cast(Any, None),
            cast(Any, None),
            _next_app,
        )
