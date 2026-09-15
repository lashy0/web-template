from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.auth.roles import Role
from app.contexts.production.kg.commands import (
    AllocateForBatch,
    CreatePrefix,
    CreateVersion,
    DeletePrefix,
    DeleteVersion,
    SetPrefixArchived,
    SetVersionArchived,
    UpdatePrefix,
    UpdateVersion,
)
from app.contexts.production.kg.exceptions import (
    KgDevEuiPrefixArchivedError,
    KgDevEuiRangeOverflowError,
)
from app.contexts.production.kg.model import KgDevEuiPrefix, KgVersion
from app.contexts.production.kg.queries import KgQueries
from app.shared.security import CurrentPrincipal


def _actor() -> CurrentPrincipal:
    return CurrentPrincipal(
        user_id=uuid4(), identity_id=uuid4(), session_id=uuid4(), role=Role.ADMINISTRATOR
    )


def _prefix(*, archived: bool = False) -> KgDevEuiPrefix:
    return KgDevEuiPrefix(
        prefix="a1b2c3d4e5",
        short_code="kg",
        name="Primary",
        archived_at=datetime.now(UTC) if archived else None,
    )


@pytest.mark.unit
async def test_prefix_create_writes_a_transactional_audit_record() -> None:
    repository = AsyncMock()
    repository.get_prefix.return_value = None
    repository.get_prefix_by_short_code.return_value = None
    item = _prefix()
    repository.save_prefix.return_value = item
    audit = AsyncMock()

    created = await CreatePrefix(repository, audit).execute(
        actor=_actor(), prefix=item.prefix, short_code=item.short_code, name=item.name
    )

    assert created is item
    repository.save_prefix.assert_awaited_once()
    audit.record.assert_awaited_once()
    assert audit.record.await_args.kwargs["action"] == "kg_prefix.created"


@pytest.mark.unit
async def test_archived_prefix_cannot_be_previewed_or_allocated() -> None:
    repository = AsyncMock()
    repository.get_prefix.return_value = _prefix(archived=True)

    with pytest.raises(KgDevEuiPrefixArchivedError):
        await KgQueries(repository).preview_allocation("a1b2c3d4e5", 1)
    with pytest.raises(KgDevEuiPrefixArchivedError):
        await AllocateForBatch(repository).execute(prefix="a1b2c3d4e5", quantity=1)


@pytest.mark.unit
async def test_preview_matches_locked_contiguous_allocation() -> None:
    repository = AsyncMock()
    repository.get_prefix.return_value = _prefix()
    repository.get_max_dev_eui_for_prefix.return_value = "a1b2c3d4e5000007"

    preview = await KgQueries(repository).preview_allocation("a1b2c3d4e5", 3)
    allocation = await AllocateForBatch(repository).execute(prefix="a1b2c3d4e5", quantity=3)

    assert preview == ("a1b2c3d4e5000008", "a1b2c3d4e500000a")
    assert allocation.dev_euis == ["a1b2c3d4e5000008", "a1b2c3d4e5000009", "a1b2c3d4e500000a"]
    repository.lock_allocation.assert_awaited_once_with("a1b2c3d4e5")


@pytest.mark.unit
async def test_allocation_rejects_suffix_overflow() -> None:
    repository = AsyncMock()
    repository.get_prefix.return_value = _prefix()
    repository.get_max_dev_eui_for_prefix.return_value = "a1b2c3d4e5ffffff"

    with pytest.raises(KgDevEuiRangeOverflowError):
        await AllocateForBatch(repository).execute(prefix="a1b2c3d4e5", quantity=1)


@pytest.mark.unit
async def test_delete_prefix_locks_allocation_before_usage_check() -> None:
    repository = AsyncMock()
    repository.get_prefix.return_value = _prefix()
    repository.count_batches_for_prefix.return_value = 0
    audit = AsyncMock()

    await DeletePrefix(repository, audit).execute(actor=_actor(), prefix="a1b2c3d4e5")

    repository.lock_allocation.assert_awaited_once_with("a1b2c3d4e5")
    repository.delete_prefix.assert_awaited_once()
    audit.record.assert_awaited_once()


@pytest.mark.unit
async def test_prefix_update_archive_and_restore_record_real_changes() -> None:
    repository = AsyncMock()
    prefix = _prefix()
    repository.get_prefix.return_value = prefix
    repository.save_prefix.side_effect = lambda item: item
    audit = AsyncMock()
    actor = _actor()

    await UpdatePrefix(repository, audit).execute(
        actor=actor, prefix=prefix.prefix, updates={"name": "Renamed"}
    )
    await SetPrefixArchived(repository, audit).execute(
        actor=actor, prefix=prefix.prefix, archived=True
    )
    await SetPrefixArchived(repository, audit).execute(
        actor=actor, prefix=prefix.prefix, archived=False
    )

    assert [call.kwargs["action"] for call in audit.record.await_args_list] == [
        "kg_prefix.updated",
        "kg_prefix.archived",
        "kg_prefix.restored",
    ]


@pytest.mark.unit
async def test_version_mutations_keep_existing_audit_semantics() -> None:
    repository = AsyncMock()
    version = KgVersion(id=uuid4(), code="v1", name="Version 1", description=None)
    repository.get_version_by_code.return_value = None
    repository.get_version.return_value = version
    repository.save_version.side_effect = lambda item: item
    repository.count_batches_for_version.return_value = 0
    audit = AsyncMock()
    actor = _actor()

    await CreateVersion(repository, audit).execute(
        actor=actor, code=version.code, name=version.name, description=version.description
    )
    await UpdateVersion(repository, audit).execute(
        actor=actor, version_id=version.id, updates={"name": "Version 1.1"}
    )
    await SetVersionArchived(repository, audit).execute(
        actor=actor, version_id=version.id, archived=True
    )
    await SetVersionArchived(repository, audit).execute(
        actor=actor, version_id=version.id, archived=False
    )
    await DeleteVersion(repository, audit).execute(actor=actor, version_id=version.id)

    assert [call.kwargs["action"] for call in audit.record.await_args_list] == [
        "kg_version.created",
        "kg_version.updated",
        "kg_version.archived",
        "kg_version.restored",
        "kg_version.deleted",
    ]
