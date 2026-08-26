from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import Identity
from app.auth.exceptions import (
    ForbiddenError,
    IdentityNotFoundError,
    IdentityProviderUnavailableError,
    UserProvisioningError,
)
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.audit.types import AuditActor, AuditEntity
from app.modules.users.models import User
from app.modules.users.service import BOOTSTRAP_ADMIN_USER_ID, UserManagementService


class _Session:
    def begin(self) -> _Session:
        return self

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    execute = AsyncMock()


class _SessionFactory:
    def __call__(self) -> _Session:
        return _Session()


def _user(*, role: Role = Role.MANAGER, state: str = "active") -> User:
    return User(
        id=uuid4(),
        identity_id=uuid4(),
        name="Alice",
        role=role,
        identity_login="alice",
        auth_state=state,
        archived_at=None,
    )


def _principal(user: User) -> CurrentPrincipal:
    return CurrentPrincipal(
        user_id=user.id,
        identity_id=user.identity_id,
        session_id=uuid4(),
        role=Role.ADMINISTRATOR,
    )


@pytest.fixture
def repositories(mocker: MockerFixture) -> tuple[MagicMock, MagicMock]:
    users = mocker.patch("app.modules.users.service.UserRepository")
    audits = mocker.patch("app.modules.users.service.AuditService")

    users.return_value.get_by_id = AsyncMock()
    users.return_value.create = AsyncMock()
    users.return_value.count = AsyncMock()
    users.return_value.update_name = AsyncMock()
    users.return_value.update_role = AsyncMock()
    users.return_value.update_identity_projection = AsyncMock()
    users.return_value.update_archived = AsyncMock()
    users.return_value.delete = AsyncMock()
    users.return_value.delete_if_exists = AsyncMock()
    users.return_value.list_all = AsyncMock()
    users.return_value.search = AsyncMock()
    users.return_value.create = AsyncMock()

    audits.from_session.return_value.record = AsyncMock()

    return users, audits


@pytest.mark.unit
async def test_set_password_updates_identity_revokes_sessions_and_records_audit(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    user = _user()
    actor = _principal(_user(role=Role.ADMINISTRATOR))
    users.return_value.get_by_id.return_value = user
    identities = SimpleNamespace(
        revoke_all_sessions=AsyncMock(),
        set_password=AsyncMock(),
    )
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    await service.set_password(
        actor=actor,
        user_id=user.id,
        password="correct-horse-battery-staple",
    )

    identities.set_password.assert_awaited_once_with(
        user.identity_id,
        password="correct-horse-battery-staple",
    )
    identities.revoke_all_sessions.assert_awaited_once_with(user.identity_id)
    audits.from_session.return_value.record.assert_awaited_once_with(
        actor=AuditActor.user(actor.user_id, name=actor.name, login=actor.login),
        action="user.password_changed",
        entity=AuditEntity.user(user.id, name=user.name, login=user.identity_login),
        new_data={"name": user.name, "login": user.identity_login},
    )


@pytest.mark.unit
async def test_create_provisions_an_inactive_identity_before_activating_it(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    user = _user(state="inactive")
    users.return_value.create.side_effect = lambda **kwargs: _create_user(user, **kwargs)
    users.return_value.get_by_id.return_value = user
    users.return_value.update_identity_projection.side_effect = lambda item, **kwargs: (
        _apply_projection(item, **kwargs)
    )
    identities = SimpleNamespace(
        create_identity=AsyncMock(
            return_value=Identity(id=user.identity_id, login="alice", active=False)
        ),
        set_active=AsyncMock(
            return_value=Identity(id=user.identity_id, login="alice", active=True)
        ),
    )
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    created = await service.create(
        actor=None,
        name="Alice",
        role=Role.MANAGER,
        login="alice",
        password="correct-horse-battery-staple",
        active=True,
    )

    assert created.auth_state == "active"
    identities.create_identity.assert_awaited_once_with(
        login="alice",
        password="correct-horse-battery-staple",
        active=False,
        user_id=user.id,
    )
    identities.set_active.assert_awaited_once_with(user.identity_id, active=True)
    audits.from_session.return_value.record.assert_awaited_once_with(
        actor=AuditActor.system(),
        action="user.created",
        entity=AuditEntity.user(user.id, name=user.name, login=user.identity_login),
        new_data={"name": user.name, "role": user.role.value, "login": user.identity_login, "active": True},
    )


@pytest.mark.unit
async def test_create_rolls_back_identity_and_local_user_when_local_creation_fails(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    identity = Identity(id=uuid4(), login="alice", active=False)
    identities = SimpleNamespace(
        create_identity=AsyncMock(return_value=identity),
        delete_identity=AsyncMock(),
    )
    users.return_value.create.side_effect = RuntimeError("database write failed")
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    with pytest.raises(UserProvisioningError) as error:
        await service.create(
            actor=None,
            name="Alice",
            role=Role.MANAGER,
            login="alice",
            password="correct-horse-battery-staple",
            active=False,
        )

    assert isinstance(error.value.__cause__, RuntimeError)
    identities.delete_identity.assert_awaited_once_with(identity.id)
    user_id = identities.create_identity.await_args.kwargs["user_id"]
    users.return_value.delete_if_exists.assert_awaited_once_with(user_id)
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_create_rolls_back_identity_and_local_user_when_activation_fails(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    user = _user(state="inactive")
    identity = Identity(id=user.identity_id, login="alice", active=False)
    users.return_value.create.side_effect = lambda **kwargs: _create_user(user, **kwargs)
    identities = SimpleNamespace(
        create_identity=AsyncMock(return_value=identity),
        set_active=AsyncMock(side_effect=IdentityProviderUnavailableError),
        delete_identity=AsyncMock(),
    )
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    with pytest.raises(UserProvisioningError) as error:
        await service.create(
            actor=None,
            name="Alice",
            role=Role.MANAGER,
            login="alice",
            password="correct-horse-battery-staple",
            active=True,
        )

    assert isinstance(error.value.__cause__, IdentityProviderUnavailableError)
    identities.delete_identity.assert_awaited_once_with(identity.id)
    users.return_value.delete_if_exists.assert_awaited_once_with(user.id)
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_create_preserves_primary_error_when_both_rollback_steps_fail(
    repositories: tuple[MagicMock, MagicMock], mocker: MockerFixture
) -> None:
    users, _ = repositories
    user = _user(state="inactive")
    identity = Identity(id=user.identity_id, login="alice", active=False)
    users.return_value.create.side_effect = lambda **kwargs: _create_user(user, **kwargs)
    users.return_value.delete_if_exists.side_effect = RuntimeError("database rollback failed")
    activation_error = IdentityProviderUnavailableError()
    identities = SimpleNamespace(
        create_identity=AsyncMock(return_value=identity),
        set_active=AsyncMock(side_effect=activation_error),
        delete_identity=AsyncMock(side_effect=RuntimeError("Kratos rollback failed")),
    )
    log = mocker.patch("app.modules.users.service.logger")
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    with pytest.raises(UserProvisioningError) as error:
        await service.create(
            actor=None,
            name="Alice",
            role=Role.MANAGER,
            login="alice",
            password="correct-horse-battery-staple",
            active=True,
        )

    assert error.value.__cause__ is activation_error
    identities.delete_identity.assert_awaited_once_with(identity.id)
    users.return_value.delete_if_exists.assert_awaited_once_with(user.id)
    assert log.bind.call_count == 3


@pytest.mark.unit
async def test_bootstrap_provisions_and_activates_the_first_administrator(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    user = _user(state="inactive")
    users.return_value.get_by_id.return_value = None
    users.return_value.count.return_value = 0
    users.return_value.create.side_effect = lambda **kwargs: _create_user(user, **kwargs)
    users.return_value.update_identity_projection.side_effect = lambda item, **kwargs: (
        _apply_projection(item, **kwargs)
    )
    metadata = {
        "provisioning": {
            "owner": "backend",
            "version": 1,
            "kind": "bootstrap",
            "user_id": str(BOOTSTRAP_ADMIN_USER_ID),
        }
    }
    identities = SimpleNamespace(
        get_identity_by_external_id=AsyncMock(side_effect=IdentityNotFoundError),
        create_identity=AsyncMock(
            return_value=Identity(
                id=user.identity_id, login="admin", active=False, metadata=metadata
            )
        ),
        set_active=AsyncMock(
            return_value=Identity(
                id=user.identity_id, login="admin", active=True, metadata=metadata
            )
        ),
    )
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    created = await service.bootstrap_first_administrator(
        name="Администратор",
        login="admin",
        password_loader=lambda: "correct-horse-battery-staple",
    )

    assert created is user
    assert created.id == BOOTSTRAP_ADMIN_USER_ID
    assert created.role is Role.ADMINISTRATOR
    assert created.auth_state == "active"
    identities.create_identity.assert_awaited_once_with(
        login="admin",
        password="correct-horse-battery-staple",
        active=False,
        user_id=BOOTSTRAP_ADMIN_USER_ID,
        provisioning_kind="bootstrap",
    )
    identities.set_active.assert_awaited_once_with(user.identity_id, active=True)
    assert audits.from_session.return_value.record.await_count == 2


@pytest.mark.unit
async def test_bootstrap_resumes_its_existing_identity_without_a_password(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, _ = repositories
    user = _user(state="inactive")
    users.return_value.get_by_id.return_value = None
    users.return_value.count.return_value = 0
    users.return_value.create.side_effect = lambda **kwargs: _create_user(user, **kwargs)
    users.return_value.update_identity_projection.side_effect = lambda item, **kwargs: (
        _apply_projection(item, **kwargs)
    )
    identity = Identity(
        id=user.identity_id,
        login="admin",
        active=False,
        metadata={
            "provisioning": {
                "owner": "backend",
                "version": 1,
                "kind": "bootstrap",
                "user_id": str(BOOTSTRAP_ADMIN_USER_ID),
            }
        },
    )
    identities = SimpleNamespace(
        get_identity_by_external_id=AsyncMock(return_value=identity),
        create_identity=AsyncMock(),
        set_active=AsyncMock(
            return_value=Identity(
                id=identity.id,
                login=identity.login,
                active=True,
                metadata=identity.metadata,
            )
        ),
    )
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    await service.bootstrap_first_administrator(
        name="Администратор", login="admin", password_loader=lambda: None
    )

    identities.create_identity.assert_not_awaited()
    identities.set_active.assert_awaited_once_with(user.identity_id, active=True)


@pytest.mark.unit
async def test_bootstrap_is_a_noop_when_another_user_already_exists(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, _ = repositories
    users.return_value.get_by_id.return_value = None
    users.return_value.count.return_value = 1
    identities = SimpleNamespace(get_identity_by_external_id=AsyncMock())
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    result = await service.bootstrap_first_administrator(
        name="Администратор", login="admin", password_loader=lambda: None
    )

    assert result is None
    identities.get_identity_by_external_id.assert_not_awaited()


@pytest.mark.unit
async def test_create_does_not_leave_an_inactive_local_projection_when_activation_fails(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, _ = repositories
    user = _user(state="inactive")
    users.return_value.create.side_effect = lambda **kwargs: _create_user(user, **kwargs)
    identities = SimpleNamespace(
        create_identity=AsyncMock(
            return_value=Identity(id=user.identity_id, login="alice", active=False)
        ),
        set_active=AsyncMock(side_effect=IdentityProviderUnavailableError),
        delete_identity=AsyncMock(),
    )
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    with pytest.raises(UserProvisioningError):
        await service.create(
            actor=None,
            name="Alice",
            role=Role.MANAGER,
            login="alice",
            password="correct-horse-battery-staple",
            active=True,
        )

    assert user.auth_state == "inactive"
    identities.set_active.assert_awaited_once_with(user.identity_id, active=True)
    identities.delete_identity.assert_awaited_once_with(user.identity_id)
    users.return_value.delete_if_exists.assert_awaited_once_with(user.id)


@pytest.mark.unit
async def test_update_changes_login_and_profile_in_one_operation(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    user = _user()
    actor = _principal(_user(role=Role.ADMINISTRATOR))
    users.return_value.get_by_id.return_value = user
    users.return_value.update_name.side_effect = lambda item, *, name: setattr(item, "name", name)
    users.return_value.update_role.side_effect = lambda item, role: setattr(item, "role", role)
    users.return_value.update_identity_projection.side_effect = lambda item, **kwargs: (
        _apply_projection(item, **kwargs)
    )
    identities = SimpleNamespace(
        update_login=AsyncMock(
            return_value=Identity(id=user.identity_id, login="alice.updated", active=True)
        )
    )
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    updated = await service.update(
        actor=actor,
        user_id=user.id,
        login="alice.updated",
        name="Alice Updated",
        role=Role.ENGINEER,
    )

    assert updated.name == "Alice Updated"
    assert updated.role is Role.ENGINEER
    assert updated.identity_login == "alice.updated"
    identities.update_login.assert_awaited_once_with(user.identity_id, login="alice.updated")
    audits.from_session.return_value.record.assert_awaited_once_with(
        actor=AuditActor.user(actor.user_id, name=actor.name, login=actor.login),
        action="user.updated",
        entity=AuditEntity.user(user.id, name="Alice Updated", login="alice.updated"),
        old_data={"name": "Alice", "role": Role.MANAGER.value, "login": "alice"},
        new_data={"name": "Alice Updated", "role": Role.ENGINEER.value, "login": "alice.updated"},
    )


@pytest.mark.unit
async def test_update_without_actual_changes_does_not_record_an_audit_event(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    user = _user()
    actor = _principal(_user(role=Role.ADMINISTRATOR))
    users.return_value.get_by_id.return_value = user
    identities = SimpleNamespace(update_login=AsyncMock())
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    updated = await service.update(
        actor=actor,
        user_id=user.id,
        login=user.identity_login,
        name=user.name,
        role=user.role,
    )

    assert updated is user
    identities.update_login.assert_not_awaited()
    users.return_value.update_name.assert_not_awaited()
    users.return_value.update_role.assert_not_awaited()
    users.return_value.update_identity_projection.assert_not_awaited()
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_set_active_cannot_deactivate_the_current_user(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, _ = repositories
    user = _user()
    users.return_value.get_by_id.return_value = user
    identities = SimpleNamespace(set_active=AsyncMock())
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    with pytest.raises(ForbiddenError, match="Cannot deactivate yourself"):
        await service.set_active(actor=_principal(user), user_id=user.id, active=False)

    identities.set_active.assert_not_awaited()


@pytest.mark.unit
async def test_set_active_without_actual_change_does_not_record_an_audit_event(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    user = _user(state="active")
    actor = _principal(_user(role=Role.ADMINISTRATOR))
    users.return_value.get_by_id.return_value = user
    identities = SimpleNamespace(set_active=AsyncMock())
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    updated = await service.set_active(actor=actor, user_id=user.id, active=True)

    assert updated is user
    identities.set_active.assert_not_awaited()
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_set_active_cannot_deactivate_the_last_active_administrator(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, _ = repositories
    user = _user(role=Role.ADMINISTRATOR)
    actor = _principal(_user(role=Role.ADMINISTRATOR))
    users.return_value.get_by_id.return_value = user
    users.return_value.search.return_value = ([user], 1)
    identities = SimpleNamespace(
        get_identity=AsyncMock(
            return_value=Identity(id=user.identity_id, login="alice", active=True)
        ),
        set_active=AsyncMock(),
    )
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    with pytest.raises(ForbiddenError, match="last active administrator"):
        await service.set_active(actor=actor, user_id=user.id, active=False)

    identities.set_active.assert_not_awaited()


@pytest.mark.unit
async def test_deactivation_persists_inactive_projection_before_revoking_sessions(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    user = _user()
    actor = _principal(_user())
    users.return_value.get_by_id.return_value = user
    users.return_value.update_identity_projection.side_effect = lambda item, **kwargs: (
        _apply_projection(item, **kwargs)
    )
    identities = SimpleNamespace(
        set_active=AsyncMock(
            return_value=Identity(id=user.identity_id, login="alice", active=False)
        ),
        revoke_all_sessions=AsyncMock(side_effect=IdentityProviderUnavailableError),
    )
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    with pytest.raises(IdentityProviderUnavailableError):
        await service.set_active(actor=actor, user_id=user.id, active=False)

    assert user.auth_state == "inactive"
    identities.set_active.assert_awaited_once_with(user.identity_id, active=False)
    identities.revoke_all_sessions.assert_awaited_once_with(user.identity_id)
    audits.from_session.return_value.record.assert_awaited_once_with(
        actor=AuditActor.user(actor.user_id, name=actor.name, login=actor.login),
        action="user.active_changed",
        entity=AuditEntity.user(user.id, name=user.name, login=user.identity_login),
        old_data={"active": True},
        new_data={"active": False},
    )


@pytest.mark.unit
async def test_archive_deactivates_user_and_records_an_audit_event(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    user = _user()
    users.return_value.get_by_id.return_value = user
    users.return_value.update_identity_projection.side_effect = lambda item, **kwargs: (
        _apply_projection(item, **kwargs)
    )
    users.return_value.update_archived.side_effect = lambda item, **kwargs: _apply_archive(
        item, **kwargs
    )
    identities = SimpleNamespace(
        set_active=AsyncMock(
            return_value=Identity(id=user.identity_id, login="alice", active=False)
        ),
        revoke_all_sessions=AsyncMock(),
    )
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    archived = await service.set_archived(actor=_principal(_user()), user_id=user.id, archived=True)

    assert archived.archived_at is not None
    assert archived.auth_state == "inactive"
    identities.set_active.assert_awaited_once_with(user.identity_id, active=False)
    identities.revoke_all_sessions.assert_awaited_once_with(user.identity_id)
    audits.from_session.return_value.record.assert_awaited_once_with(
        actor=ANY,
        action="user.archived",
        entity=AuditEntity.user(user.id, name=user.name, login=user.identity_login),
        new_data={"name": user.name, "login": user.identity_login},
    )


@pytest.mark.unit
async def test_restore_removes_archive_mark_without_activating_user(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    user = _user()
    user.archived_at = datetime.now(UTC)
    users.return_value.get_by_id.return_value = user
    users.return_value.update_archived.side_effect = lambda item, **kwargs: _apply_archive(
        item, **kwargs
    )
    identities = SimpleNamespace(set_active=AsyncMock())
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    restored = await service.set_archived(
        actor=_principal(_user()), user_id=user.id, archived=False
    )

    assert restored.archived_at is None
    identities.set_active.assert_not_awaited()
    audits.from_session.return_value.record.assert_awaited_once_with(
        actor=ANY,
        action="user.restored",
        entity=AuditEntity.user(user.id, name=user.name, login=user.identity_login),
        new_data={"name": user.name, "login": user.identity_login},
    )


@pytest.mark.unit
async def test_delete_removes_identity_and_local_user_after_recording_audit_event(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    user = _user()
    actor = _principal(_user())
    users.return_value.get_by_id.return_value = user
    identities = SimpleNamespace(delete_identity=AsyncMock())
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    await service.delete(actor=actor, user_id=user.id)

    identities.delete_identity.assert_awaited_once_with(user.identity_id)
    audits.from_session.return_value.record.assert_awaited_once_with(
        actor=AuditActor.user(actor.user_id, name=actor.name, login=actor.login),
        action="user.deleted",
        entity=AuditEntity.user(user.id, name=user.name, login=user.identity_login),
        old_data={"name": user.name, "role": user.role.value, "login": user.identity_login},
    )
    users.return_value.delete.assert_awaited_once_with(user)


@pytest.mark.unit
async def test_delete_cannot_delete_the_current_user(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, _ = repositories
    user = _user()
    users.return_value.get_by_id.return_value = user
    identities = SimpleNamespace(delete_identity=AsyncMock())
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    with pytest.raises(ForbiddenError, match="Cannot delete yourself"):
        await service.delete(actor=_principal(user), user_id=user.id)

    identities.delete_identity.assert_not_awaited()


@pytest.mark.unit
async def test_reconcile_marks_missing_identity_inactive_and_logs_a_sync_error(
    repositories: tuple[MagicMock, MagicMock],
) -> None:
    users, audits = repositories
    user = _user(state="active")
    users.return_value.list_all.return_value = [user]
    users.return_value.update_identity_projection.side_effect = lambda item, **kwargs: (
        _apply_projection(item, **kwargs)
    )
    identities = SimpleNamespace(list_identities=AsyncMock(return_value=[]))
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    await service.reconcile()

    assert user.auth_state == "inactive"
    assert user.identity_login == "alice"
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_reconcile_logs_each_sync_mismatch_only_once_per_process(
    repositories: tuple[MagicMock, MagicMock], mocker: MockerFixture
) -> None:
    users, _ = repositories
    user = _user(state="inactive")
    users.return_value.list_all.return_value = [user]
    identities = SimpleNamespace(list_identities=AsyncMock(return_value=[]))
    log = mocker.patch("app.modules.users.service.logger")
    service = UserManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), identities
    )

    await service.reconcile()
    await service.reconcile()

    log.bind.return_value.error.assert_called_once_with("Local user has no Kratos identity")


def _apply_projection(user: User, *, login: str | None, state: str, **_: object) -> User:
    user.identity_login = login
    user.auth_state = state
    return user


def _apply_archive(user: User, *, archived_at: datetime | None) -> User:
    user.archived_at = archived_at
    return user


def _create_user(user: User, *, user_id: UUID, role: Role, **_: object) -> User:
    user.id = user_id
    user.role = role
    return user
