"""Rules governing DevEUI prefixes."""

import pytest

from app.domains.production.kg.commands import (
    CreatePrefix,
    DeletePrefix,
    SetPrefixArchived,
    UpdatePrefix,
)
from app.domains.production.kg.exceptions import (
    KgDevEuiPrefixConflictError,
    KgDevEuiPrefixInUseError,
    KgDevEuiPrefixNotFoundError,
)
from app.shared.security import ForbiddenError, Role
from tests.support.actors import principal
from tests.support.audit import RecordingAudit
from tests.support.kg import InMemoryKgStore


@pytest.fixture
def store() -> InMemoryKgStore:
    return InMemoryKgStore()


@pytest.fixture
def audit() -> RecordingAudit:
    return RecordingAudit()


@pytest.mark.unit
async def test_a_created_prefix_becomes_available_for_allocation(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    created = await CreatePrefix(store, audit).execute(
        actor=principal(), prefix="a1b2c3d4e5", short_code="kg", name="Primary"
    )

    assert store.prefixes["a1b2c3d4e5"] is created
    assert created.archived_at is None
    assert audit.only.action == "kg_prefix.created"
    assert audit.only.new_data == {
        "prefix": "a1b2c3d4e5",
        "short_code": "kg",
        "name": "Primary",
    }


@pytest.mark.unit
async def test_a_prefix_cannot_be_registered_twice(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    store.given_prefix("a1b2c3d4e5", short_code="kg")

    with pytest.raises(KgDevEuiPrefixConflictError):
        await CreatePrefix(store, audit).execute(
            actor=principal(), prefix="a1b2c3d4e5", short_code="other", name="Duplicate"
        )

    assert audit.nothing_was_audited


@pytest.mark.unit
async def test_a_short_code_cannot_be_shared_by_two_prefixes(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    store.given_prefix("a1b2c3d4e5", short_code="kg")

    with pytest.raises(KgDevEuiPrefixConflictError):
        await CreatePrefix(store, audit).execute(
            actor=principal(), prefix="ffeeddccbb", short_code="kg", name="Same code"
        )

    assert "ffeeddccbb" not in store.prefixes
    assert audit.nothing_was_audited


@pytest.mark.unit
async def test_renaming_a_prefix_audits_only_the_fields_that_changed(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    prefix = store.given_prefix("a1b2c3d4e5", name="Primary")

    updated = await UpdatePrefix(store, audit).execute(
        actor=principal(), prefix=prefix.prefix, updates={"name": "Renamed"}
    )

    assert updated.name == "Renamed"
    assert audit.only.old_data == {"name": "Primary"}
    assert audit.only.new_data == {"name": "Renamed"}


@pytest.mark.unit
async def test_rewriting_a_prefix_field_with_its_current_value_is_not_audited(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    prefix = store.given_prefix("a1b2c3d4e5", name="Primary")

    await UpdatePrefix(store, audit).execute(
        actor=principal(), prefix=prefix.prefix, updates={"name": "Primary"}
    )

    assert audit.nothing_was_audited


@pytest.mark.unit
async def test_archiving_a_prefix_twice_is_audited_once(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    prefix = store.given_prefix("a1b2c3d4e5")

    await SetPrefixArchived(store, audit).execute(
        actor=principal(), prefix=prefix.prefix, archived=True
    )
    await SetPrefixArchived(store, audit).execute(
        actor=principal(), prefix=prefix.prefix, archived=True
    )

    assert store.prefixes[prefix.prefix].archived_at is not None
    assert audit.actions == ["kg_prefix.archived"]


@pytest.mark.unit
async def test_restoring_a_prefix_clears_its_archive_and_is_audited(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    prefix = store.given_prefix("a1b2c3d4e5", archived=True)

    restored = await SetPrefixArchived(store, audit).execute(
        actor=principal(), prefix=prefix.prefix, archived=False
    )

    assert restored.archived_at is None
    assert audit.actions == ["kg_prefix.restored"]


@pytest.mark.unit
async def test_a_prefix_used_by_a_batch_cannot_be_deleted(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    prefix = store.given_prefix("a1b2c3d4e5")
    store.given_batches_using_prefix(prefix.prefix, count=1)

    with pytest.raises(KgDevEuiPrefixInUseError):
        await DeletePrefix(store, audit).execute(actor=principal(), prefix=prefix.prefix)

    assert prefix.prefix in store.prefixes
    assert audit.nothing_was_audited


@pytest.mark.unit
async def test_an_unused_prefix_is_deleted_and_audited(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    prefix = store.given_prefix("a1b2c3d4e5")

    await DeletePrefix(store, audit).execute(actor=principal(), prefix=prefix.prefix)

    assert prefix.prefix not in store.prefixes
    assert audit.only.action == "kg_prefix.deleted"


@pytest.mark.unit
async def test_prefix_deletion_takes_the_allocation_lock_before_reading_usage(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    """Checking usage before locking would race with a concurrent allocation."""
    prefix = store.given_prefix("a1b2c3d4e5")

    await DeletePrefix(store, audit).execute(actor=principal(), prefix=prefix.prefix)

    assert store.happened_before("lock_allocation", "count_batches_for_prefix")
    assert store.happened_before("lock_allocation", "delete_prefix")


@pytest.mark.unit
async def test_deleting_a_missing_prefix_reports_not_found(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    with pytest.raises(KgDevEuiPrefixNotFoundError):
        await DeletePrefix(store, audit).execute(actor=principal(), prefix="a1b2c3d4e5")


@pytest.mark.unit
async def test_an_engineer_may_not_manage_prefixes(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    with pytest.raises(ForbiddenError):
        await CreatePrefix(store, audit).execute(
            actor=principal(Role.ENGINEER), prefix="a1b2c3d4e5", short_code="kg", name="Primary"
        )

    assert store.prefixes == {}
    assert audit.nothing_was_audited
