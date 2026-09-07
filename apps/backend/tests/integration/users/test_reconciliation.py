import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from app.auth.contracts import Identity
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.audit.models import AuditEvent
from app.modules.audit.service import AuditService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.services import UserManagementService
from app.modules.users.services.reconciliation import UserReconciliationService

pytestmark = pytest.mark.integration


@pytest.fixture
async def users(database_session_factory):
    factory = database_session_factory
    records = [
        User(
            id=uuid4(),
            identity_id=uuid4(),
            name=f"User {index}",
            role=Role.MANAGER,
            identity_login=f"user{index}",
            auth_state="active",
        )
        for index in range(2)
    ]
    async with factory() as session, session.begin():
        session.add_all(records)
    try:
        yield records
    finally:
        async with factory() as session, session.begin():
            await session.execute(delete(User).where(User.id.in_([user.id for user in records])))
            await session.execute(
                delete(AuditEvent).where(
                    AuditEvent.entity_id.in_([str(user.id) for user in records])
                )
            )


def actor():
    return CurrentPrincipal(
        user_id=uuid4(), identity_id=uuid4(), session_id=uuid4(), role=Role.ADMINISTRATOR
    )


@pytest.mark.parametrize("operation", ["edit", "login", "enable", "disable", "archive", "delete"])
async def test_api_completes_during_provider_read_and_stale_reconcile_is_skipped(
    database_session_factory,
    users,
    operation,
):
    factory = database_session_factory
    user = users[0]
    if operation == "enable":
        async with factory() as session, session.begin():
            session.add(user)
            user.auth_state = "inactive"
    reading, release = asyncio.Event(), asyncio.Event()
    identities = AsyncMock()

    async def provider_snapshot(**_):
        snapshot = [
            Identity(
                id=item.identity_id, login=item.identity_login, active=item.auth_state == "active"
            )
            for item in users
        ]
        reading.set()
        await release.wait()
        return snapshot

    identities.list_identities.side_effect = provider_snapshot
    identities.set_active.return_value = Identity(
        id=user.identity_id, login=user.identity_login, active=operation == "enable"
    )
    identities.update_login.return_value = Identity(
        id=user.identity_id, login="newlogin", active=True
    )
    service = UserManagementService(factory, identities)
    task = asyncio.create_task(service.reconcile())
    try:
        await asyncio.wait_for(reading.wait(), 2)
        async with asyncio.timeout(2):
            if operation == "edit":
                await service.update(
                    actor=actor(), user_id=user.id, name="Changed", login=None, role=None
                )
            elif operation == "login":
                await service.update(
                    actor=actor(), user_id=user.id, name=None, login="newlogin", role=None
                )
            elif operation in {"enable", "disable"}:
                await service.set_active(
                    actor=actor(), user_id=user.id, active=operation == "enable"
                )
            elif operation == "archive":
                await service.set_archived(actor=actor(), user_id=user.id, archived=True)
            else:
                await service.delete(actor=actor(), user_id=user.id)
        release.set()
        result = await asyncio.wait_for(task, 2)
        assert result.conflicts == 1
        async with factory() as session:
            saved = await session.get(User, user.id)
            if operation == "delete":
                assert saved is None
            else:
                assert saved.version > user.version
                assert saved.auth_state == (
                    "active" if operation in {"edit", "login", "enable"} else "inactive"
                )
                if operation == "edit":
                    assert saved.name == "Changed"
                if operation == "archive":
                    assert saved.archived_at is not None
                if operation == "login":
                    assert saved.identity_login == "newlogin"
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(
                        AuditEvent.entity_id == str(user.id),
                        AuditEvent.action == "user.reconciled",
                    )
                )
                == 0
            )
    finally:
        release.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_busy_user_is_skipped_and_other_user_can_be_edited(database_session_factory, users):
    factory = database_session_factory
    identities = AsyncMock()
    identities.list_identities.return_value = [
        Identity(id=item.identity_id, login=item.identity_login, active=False) for item in users
    ]
    service = UserManagementService(factory, identities)
    async with factory() as session, session.begin():
        await UserRepository(session).get_by_id(users[0].id, for_update=True)
        async with asyncio.timeout(2):
            await service.update(
                actor=actor(), user_id=users[1].id, name="Independent", login=None, role=None
            )
            result = await service.reconcile()
        assert result.conflicts == 1
        assert result.updated == 1


async def test_same_user_api_operations_are_serialized(database_session_factory, users):
    factory = database_session_factory
    entered, release = asyncio.Event(), asyncio.Event()
    identities = AsyncMock()

    async def disable(identity_id, **_):
        entered.set()
        await release.wait()
        return Identity(id=identity_id, login=users[0].identity_login, active=False)

    identities.set_active.side_effect = disable
    service = UserManagementService(factory, identities)
    first = asyncio.create_task(
        service.set_active(actor=actor(), user_id=users[0].id, active=False)
    )
    second = None
    try:
        await asyncio.wait_for(entered.wait(), 2)
        second = asyncio.create_task(service.delete(actor=actor(), user_id=users[0].id))
        done, _ = await asyncio.wait([second], timeout=0.15)
        assert not done
        identities.delete_identity.assert_not_awaited()
        release.set()
        await asyncio.wait_for(asyncio.gather(first, second), 2)
        identities.delete_identity.assert_awaited_once_with(users[0].identity_id)
    finally:
        release.set()
        for task in (first, second):
            if task is not None:
                task.cancel()
        await asyncio.gather(
            *[task for task in (first, second) if task is not None], return_exceptions=True
        )


async def test_reconcile_repairs_provider_success_after_database_rollback(
    database_session_factory, users, monkeypatch
):
    factory = database_session_factory
    identities = AsyncMock()
    identities.set_active.return_value = Identity(
        id=users[0].identity_id, login=users[0].identity_login, active=False
    )
    service = UserManagementService(factory, identities)
    with monkeypatch.context() as patch:
        patch.setattr(
            AuditService, "record", AsyncMock(side_effect=RuntimeError("database write failed"))
        )
        with pytest.raises(RuntimeError, match="database write failed"):
            await service.set_active(actor=actor(), user_id=users[0].id, active=False)
    identities.set_active.assert_awaited_once()
    async with factory() as session:
        saved = await session.get(User, users[0].id)
        assert saved.auth_state == "active"
        assert saved.version == users[0].version
    identities.list_identities.return_value = [
        Identity(id=item.identity_id, login=item.identity_login, active=False) for item in users
    ]
    result = await service.reconcile()
    assert result.updated == 2
    async with factory() as session:
        assert (await session.get(User, users[0].id)).auth_state == "inactive"
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.entity_id == str(users[0].id),
                    AuditEvent.action == "user.reconciled",
                )
            )
            == 1
        )


async def test_conditional_update_rejects_old_version(database_session_factory, users):
    factory = database_session_factory
    async with factory() as reader:
        stale = await reader.get(User, users[0].id)
        async with factory() as writer, writer.begin():
            repository = UserRepository(writer)
            current = await repository.get_by_id(stale.id, for_update=True)
            await repository.update_name(current, name="New name")
        assert not await UserRepository(reader).reconcile_projection(
            stale,
            login="obsolete",
            state="inactive",
            synced_at=datetime.now(UTC),
        )


async def test_simultaneous_reconcilers_do_not_duplicate_audit(database_session_factory, users):
    identities = AsyncMock()
    identities.list_identities.return_value = [
        Identity(id=item.identity_id, login=item.identity_login, active=False) for item in users
    ]
    services = [UserReconciliationService(database_session_factory, identities) for _ in range(2)]
    await asyncio.wait_for(asyncio.gather(*[service.reconcile() for service in services]), 3)
    async with database_session_factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.entity_id.in_([str(user.id) for user in users]),
                    AuditEvent.action == "user.reconciled",
                )
            )
            == 2
        )
