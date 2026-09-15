"""Rules governing individual KG units."""

import pytest

from app.domains.production.kg.commands import DeleteKg, SetKgState
from app.domains.production.kg.exceptions import KgCannotBeDeletedError, KgNotFoundError
from app.domains.production.kg.model import KgState
from tests.support.actors import principal
from tests.support.audit import RecordingAudit
from tests.support.kg import InMemoryKgStore, StubVerificationHistory

DEV_EUI = "a1b2c3d4e5000001"


@pytest.fixture
def store() -> InMemoryKgStore:
    return InMemoryKgStore()


@pytest.fixture
def audit() -> RecordingAudit:
    return RecordingAudit()


@pytest.mark.unit
async def test_scrapping_a_kg_persists_the_new_state_and_audits_it(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    store.given_unit(DEV_EUI)

    updated = await SetKgState(store, audit).execute(
        actor=principal(), dev_eui=DEV_EUI, state=KgState.SCRAPPED
    )

    assert updated.state is KgState.SCRAPPED
    assert store.units[DEV_EUI].state is KgState.SCRAPPED
    assert audit.only.action == "kg.state_changed"


@pytest.mark.unit
async def test_changing_the_state_of_a_missing_kg_reports_not_found(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    with pytest.raises(KgNotFoundError):
        await SetKgState(store, audit).execute(
            actor=principal(), dev_eui=DEV_EUI, state=KgState.SCRAPPED
        )

    assert audit.nothing_was_audited


@pytest.mark.unit
async def test_a_kg_that_was_verified_cannot_be_deleted(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    """Deleting it would drop the evidence trail of a tested device."""
    store.given_unit(DEV_EUI)
    history = StubVerificationHistory(dev_euis_with_history={DEV_EUI})

    with pytest.raises(KgCannotBeDeletedError):
        await DeleteKg(store, history, audit).execute(actor=principal(), dev_eui=DEV_EUI)

    assert DEV_EUI in store.units
    assert audit.nothing_was_audited


@pytest.mark.unit
async def test_a_scrapped_kg_cannot_be_deleted(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    """Scrapping is the accounting record; deletion would erase it."""
    store.given_unit(DEV_EUI, state=KgState.SCRAPPED)

    with pytest.raises(KgCannotBeDeletedError):
        await DeleteKg(store, StubVerificationHistory(), audit).execute(
            actor=principal(), dev_eui=DEV_EUI
        )

    assert DEV_EUI in store.units
    assert audit.nothing_was_audited


@pytest.mark.unit
async def test_a_registered_kg_without_verification_history_is_deleted_and_audited(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    store.given_unit(DEV_EUI, state=KgState.REGISTERED)

    await DeleteKg(store, StubVerificationHistory(), audit).execute(
        actor=principal(), dev_eui=DEV_EUI
    )

    assert DEV_EUI not in store.units
    assert audit.only.action == "kg.deleted"
    assert audit.only.old_data is not None
    assert audit.only.old_data["dev_eui"] == DEV_EUI


@pytest.mark.unit
async def test_the_deletion_audit_snapshots_the_row_that_was_removed(
    store: InMemoryKgStore, audit: RecordingAudit
) -> None:
    """The deleted row is unrecoverable, so the audit must carry its values."""
    unit = store.given_unit(DEV_EUI)

    await DeleteKg(store, StubVerificationHistory(), audit).execute(
        actor=principal(), dev_eui=DEV_EUI
    )

    assert audit.only.old_data == {
        "dev_eui": DEV_EUI,
        "batch_id": str(unit.batch_id),
        "state": KgState.REGISTERED.value,
    }
