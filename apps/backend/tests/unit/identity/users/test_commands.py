from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.auth.exceptions import IdentityProviderUnavailableError
from app.domains.identity.users.commands.create import CreateUser
from app.domains.identity.users.commands.set_archived import SetUserArchived
from app.domains.identity.users.commands.update import UpdateUser
from app.domains.identity.users.exceptions import UserProvisioningError
from app.domains.identity.users.model import User
from app.shared.security import CurrentPrincipal, Identity, Role


class _Session:
    def begin(self) -> _Session:
        return self

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class _SessionFactory:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> _Session:
        self.calls += 1
        return _Session()


def _user() -> User:
    return User(
        id=uuid4(),
        identity_id=uuid4(),
        name="Alice",
        role=Role.MANAGER,
        identity_login="alice",
        auth_state="active",
        archived_at=None,
        version=1,
    )


def _actor() -> CurrentPrincipal:
    return CurrentPrincipal(
        user_id=uuid4(), identity_id=uuid4(), session_id=uuid4(), role=Role.ADMINISTRATOR
    )


@pytest.mark.unit
async def test_create_stops_before_local_transaction_when_kratos_create_fails() -> None:
    sessions = _SessionFactory()
    identities = SimpleNamespace(
        create_identity=AsyncMock(side_effect=IdentityProviderUnavailableError)
    )

    with pytest.raises(IdentityProviderUnavailableError):
        await CreateUser(sessions, identities).execute(
            actor=_actor(),
            name="Alice",
            role=Role.MANAGER,
            login="alice",
            password="correct-horse-battery-staple",
            active=False,
        )

    assert sessions.calls == 0


@pytest.mark.unit
async def test_create_compensates_kratos_when_local_transaction_fails(mocker) -> None:
    sessions = _SessionFactory()
    identity = Identity(id=uuid4(), login="alice", active=False)
    identities = SimpleNamespace(
        create_identity=AsyncMock(return_value=identity), delete_identity=AsyncMock()
    )
    repository = mocker.patch("app.domains.identity.users.commands.create.UserRepository")
    repository.return_value.create = AsyncMock(side_effect=RuntimeError("db failed"))
    repository.return_value.delete_if_exists = AsyncMock()

    with pytest.raises(UserProvisioningError):
        await CreateUser(sessions, identities).execute(
            actor=_actor(),
            name="Alice",
            role=Role.MANAGER,
            login="alice",
            password="correct-horse-battery-staple",
            active=False,
        )

    identities.delete_identity.assert_awaited_once_with(identity.id)
    repository.return_value.delete_if_exists.assert_awaited_once()


@pytest.mark.unit
async def test_update_leaves_local_values_unchanged_when_kratos_update_fails(mocker) -> None:
    sessions = _SessionFactory()
    user = _user()
    repository = mocker.patch("app.domains.identity.users.commands.update.UserRepository")
    repository.return_value.get_by_id = AsyncMock(return_value=user)
    identities = SimpleNamespace(
        update_login=AsyncMock(side_effect=IdentityProviderUnavailableError)
    )

    with pytest.raises(IdentityProviderUnavailableError):
        await UpdateUser(sessions, identities).execute(
            actor=_actor(), user_id=user.id, login="alice.updated", name=None, role=None
        )

    assert user.identity_login == "alice"
    repository.return_value.update_identity_projection.assert_not_called()


@pytest.mark.unit
async def test_update_keeps_baseline_no_compensation_after_local_failure(mocker) -> None:
    sessions = _SessionFactory()
    user = _user()
    identity = Identity(id=user.identity_id, login="alice.updated", active=True)
    repository = mocker.patch("app.domains.identity.users.commands.update.UserRepository")
    repository.return_value.get_by_id = AsyncMock(return_value=user)
    repository.return_value.update_identity_projection = AsyncMock(
        side_effect=RuntimeError("db failed")
    )
    identities = SimpleNamespace(update_login=AsyncMock(return_value=identity))

    with pytest.raises(RuntimeError, match="db failed"):
        await UpdateUser(sessions, identities).execute(
            actor=_actor(), user_id=user.id, login="alice.updated", name=None, role=None
        )

    identities.update_login.assert_awaited_once_with(user.identity_id, login="alice.updated")
    assert user.identity_login == "alice"


@pytest.mark.unit
async def test_archive_kratos_failure_preserves_local_lifecycle_state(mocker) -> None:
    sessions = _SessionFactory()
    user = _user()
    repository = mocker.patch("app.domains.identity.users.commands.set_archived.UserRepository")
    repository.return_value.get_by_id = AsyncMock(return_value=user)
    identities = SimpleNamespace(set_active=AsyncMock(side_effect=IdentityProviderUnavailableError))

    with pytest.raises(IdentityProviderUnavailableError):
        await SetUserArchived(sessions, identities).execute(
            actor=_actor(), user_id=user.id, archived=True
        )

    assert user.archived_at is None
    assert user.auth_state == "active"
    repository.return_value.update_archived.assert_not_called()
