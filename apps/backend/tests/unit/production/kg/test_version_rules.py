"""Rules governing KG versions."""

import pytest

from app.domains.production.kg.commands import (
    CreateVersion,
    DeleteVersion,
    SetVersionArchived,
    UpdateVersion,
)
from app.domains.production.kg.exceptions import (
    KgVersionConflictError,
    KgVersionInUseError,
    KgVersionNotFoundError,
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
async def test_a_created_version_is_stored_unarchived_and_audited(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    created = await CreateVersion(store, audit).execute(
        actor=principal(), code="KG-1", name="Version 1", description="First"
    )

    assert store.versions[created.id] is created
    assert created.archived_at is None
    assert audit.only.action == "kg_version.created"
    assert audit.only.new_data == {
        "code": "KG-1",
        "name": "Version 1",
        "description": "First",
    }


@pytest.mark.unit
async def test_a_version_code_must_be_unique(store: InMemoryKgStore, audit: RecordingAudit) -> None:
    store.given_version("KG-1")

    with pytest.raises(KgVersionConflictError):
        await CreateVersion(store, audit).execute(
            actor=principal(), code="KG-1", name="Duplicate", description=None
        )

    assert len(store.versions) == 1
    assert audit.nothing_was_audited


@pytest.mark.unit
async def test_renaming_a_version_audits_only_the_fields_that_changed(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    version = store.given_version("KG-1", name="Version 1")

    updated = await UpdateVersion(store, audit).execute(
        actor=principal(), version_id=version.id, updates={"name": "Version 1.1"}
    )

    assert updated.name == "Version 1.1"
    assert audit.only.old_data == {"name": "Version 1"}
    assert audit.only.new_data == {"name": "Version 1.1"}


@pytest.mark.unit
async def test_rewriting_a_version_field_with_its_current_value_is_not_audited(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    version = store.given_version("KG-1", name="Version 1")

    await UpdateVersion(store, audit).execute(
        actor=principal(), version_id=version.id, updates={"name": "Version 1"}
    )

    assert audit.nothing_was_audited


@pytest.mark.unit
async def test_archiving_a_version_twice_is_audited_once(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    version = store.given_version("KG-1")

    await SetVersionArchived(store, audit).execute(
        actor=principal(), version_id=version.id, archived=True
    )
    await SetVersionArchived(store, audit).execute(
        actor=principal(), version_id=version.id, archived=True
    )

    assert store.versions[version.id].archived_at is not None
    assert audit.actions == ["kg_version.archived"]


@pytest.mark.unit
async def test_restoring_a_version_clears_its_archive_and_is_audited(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    version = store.given_version("KG-1", archived=True)

    restored = await SetVersionArchived(store, audit).execute(
        actor=principal(), version_id=version.id, archived=False
    )

    assert restored.archived_at is None
    assert audit.actions == ["kg_version.restored"]
    assert audit.only.new_data == {"archived_at": None}


@pytest.mark.unit
async def test_a_version_used_by_a_batch_cannot_be_deleted(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    version = store.given_version("KG-1")
    store.given_batches_using_version(version.id, count=2)

    with pytest.raises(KgVersionInUseError):
        await DeleteVersion(store, audit).execute(actor=principal(), version_id=version.id)

    assert version.id in store.versions
    assert audit.nothing_was_audited


@pytest.mark.unit
async def test_an_unused_version_is_deleted_and_audited(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    version = store.given_version("KG-1")

    await DeleteVersion(store, audit).execute(actor=principal(), version_id=version.id)

    assert version.id not in store.versions
    assert audit.only.action == "kg_version.deleted"


@pytest.mark.unit
async def test_operating_on_a_missing_version_reports_not_found(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    missing = store.given_version("KG-1").id
    store.versions.clear()

    with pytest.raises(KgVersionNotFoundError):
        await DeleteVersion(store, audit).execute(actor=principal(), version_id=missing)

    with pytest.raises(KgVersionNotFoundError):
        await UpdateVersion(store, audit).execute(
            actor=principal(), version_id=missing, updates={"name": "New"}
        )


@pytest.mark.unit
async def test_an_engineer_may_not_manage_versions(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    with pytest.raises(ForbiddenError):
        await CreateVersion(store, audit).execute(
            actor=principal(Role.ENGINEER), code="KG-1", name="Version 1", description=None
        )

    assert store.versions == {}
    assert audit.nothing_was_audited
