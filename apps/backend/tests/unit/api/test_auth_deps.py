from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from app.api.auth_deps import get_current_principal
from app.auth.contracts import AuthSession, Identity
from app.auth.exceptions import AccountDisabledError, InvalidSessionError, UserNotProvisionedError
from app.auth.roles import Role


class _SessionFactory:
    def __call__(self) -> _SessionFactory:
        return self

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *args: object) -> None:
        return None


def _request(cookie: str | None) -> SimpleNamespace:
    cookies = {} if cookie is None else {"ory_kratos_session": cookie}
    return SimpleNamespace(
        cookies=cookies,
        app=SimpleNamespace(
            state=SimpleNamespace(
                settings=SimpleNamespace(KRATOS_SESSION_COOKIE="ory_kratos_session")
            )
        ),
    )


@pytest.mark.unit
async def test_current_principal_rejects_a_missing_session_cookie() -> None:
    with pytest.raises(InvalidSessionError):
        await get_current_principal(
            cast(Any, _request(None)),
            cast(Any, SimpleNamespace(session_factory=_SessionFactory())),
            AsyncMock(),
        )


@pytest.mark.unit
async def test_current_principal_rejects_an_inactive_identity() -> None:
    verifier = AsyncMock()
    verifier.verify_session.return_value = AuthSession(
        id=uuid4(),
        identity=Identity(id=uuid4(), login="alice", active=False),
        expires_at=datetime.now(UTC),
    )

    with pytest.raises(AccountDisabledError):
        await get_current_principal(
            cast(Any, _request("opaque-value")),
            cast(Any, SimpleNamespace(session_factory=_SessionFactory())),
            verifier,
        )

    verifier.verify_session.assert_awaited_once_with(
        cookie_header="ory_kratos_session=opaque-value"
    )


@pytest.mark.unit
async def test_current_principal_rejects_unprovisioned_kratos_identity(
    mocker: MockerFixture,
) -> None:
    identity_id = uuid4()
    verifier = AsyncMock()
    verifier.verify_session.return_value = AuthSession(
        id=uuid4(),
        identity=Identity(id=identity_id, login="alice", active=True),
        expires_at=datetime.now(UTC),
    )
    repository = mocker.patch("app.api.auth_deps.UserRepository")
    repository.return_value.get_by_identity_id = AsyncMock(return_value=None)

    with pytest.raises(UserNotProvisionedError):
        await get_current_principal(
            cast(Any, _request("opaque-value")),
            cast(Any, SimpleNamespace(session_factory=_SessionFactory())),
            verifier,
        )

    repository.return_value.get_by_identity_id.assert_awaited_once_with(identity_id)


@pytest.mark.unit
async def test_current_principal_uses_the_local_user_role(mocker: MockerFixture) -> None:
    user_id = uuid4()
    identity_id = uuid4()
    session_id = uuid4()
    verifier = AsyncMock()
    verifier.verify_session.return_value = AuthSession(
        id=session_id,
        identity=Identity(id=identity_id, login="alice", active=True),
        expires_at=datetime.now(UTC),
    )
    repository = mocker.patch("app.api.auth_deps.UserRepository")
    repository.return_value.get_by_identity_id = AsyncMock(
        return_value=SimpleNamespace(
            id=user_id,
            role=Role.MANAGER,
            name="Alice",
            identity_login="alice",
        )
    )

    principal = await get_current_principal(
        cast(Any, _request("opaque-value")),
        cast(Any, SimpleNamespace(session_factory=_SessionFactory())),
        verifier,
    )

    assert principal.user_id == user_id
    assert principal.identity_id == identity_id
    assert principal.session_id == session_id
    assert principal.role == Role.MANAGER
    assert principal.name == "Alice"
    assert principal.login == "alice"
