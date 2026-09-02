from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.kg.models import KgStatus, KgUnit
from app.modules.pak.models import PakDevice, PakDeviceKind
from app.modules.verification.exceptions import (
    VerificationSessionAlreadyRunningError,
    VerificationSessionIncompleteError,
    VerificationStepAlreadyCompletedError,
    VerificationStepInProgressError,
)
from app.modules.verification.models import (
    VerificationSession,
    VerificationSessionStatus,
    VerificationStep,
    VerificationStepStatus,
)
from app.modules.verification.service import VerificationManagementService


class _Session:
    def begin(self) -> _Session:
        return self

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class _SessionFactory:
    def __call__(self) -> _Session:
        return _Session()


def _pak() -> PakDevice:
    return PakDevice(
        id=uuid4(),
        code="PAK-OTK-01",
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id="pak-test",
        encrypted_access_key="ciphertext",
        is_active=True,
        archived_at=None,
    )


def _kg(*, status: KgStatus = KgStatus.REGISTERED) -> KgUnit:
    now = datetime.now(UTC)
    return KgUnit(
        dev_eui="a1b2c3d4e5f60708",
        short_id="kg-000001",
        batch_id=uuid4(),
        status=status,
        created_at=now,
        updated_at=now,
    )


def _verification_session(
    pak: PakDevice,
    *,
    kg_dev_eui: str = "a1b2c3d4e5f60708",
    slot_no: int = 1,
    total_steps: int = 2,
    status: VerificationSessionStatus = VerificationSessionStatus.RUNNING,
    last_activity_at: datetime | None = None,
) -> VerificationSession:
    now = datetime.now(UTC)
    return VerificationSession(
        id=uuid4(),
        kg_dev_eui=kg_dev_eui,
        pak_id=pak.id,
        slot_no=slot_no,
        firmware_version="1.2.3",
        total_steps=total_steps,
        status=status,
        started_at=now,
        last_activity_at=last_activity_at or now,
        created_at=now,
        updated_at=now,
    )


def _step(
    verification_session: VerificationSession,
    *,
    step_no: int = 1,
    status: VerificationStepStatus = VerificationStepStatus.RUNNING,
) -> VerificationStep:
    now = datetime.now(UTC)
    return VerificationStep(
        id=uuid4(),
        session_id=verification_session.id,
        pak_test_id=uuid4(),
        defect_group_id=uuid4(),
        step_no=step_no,
        test_name="voltage",
        test_label="Supply voltage",
        error_group_code="POWER",
        status=status,
        started_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def repositories(mocker: MockerFixture) -> tuple[MagicMock, MagicMock, MagicMock]:
    verification_sessions = mocker.patch(
        "app.modules.verification.service.VerificationSessionRepository"
    )
    verification_steps = mocker.patch(
        "app.modules.verification.service.VerificationStepRepository"
    )
    kg = mocker.patch("app.modules.verification.service.KgRepository")
    for method in (
        "lock_session_open",
        "get_running_by_kg",
        "get_running_by_pak_slot",
        "create",
        "touch_activity",
        "get_by_id_for_update",
        "complete",
        "list_stale_running_for_update",
    ):
        setattr(verification_sessions.return_value, method, AsyncMock())
    for method in (
        "get_by_session_and_step_no",
        "exists_running_by_session",
        "create",
        "get_by_session_and_step_no_for_update",
        "complete",
        "get_running_by_session_for_update",
        "count_by_session_and_status",
    ):
        setattr(verification_steps.return_value, method, AsyncMock())
    kg.return_value.get_by_dev_eui = AsyncMock()
    kg.return_value.update_status = AsyncMock()
    verification_sessions.return_value.get_running_by_kg.return_value = None
    verification_sessions.return_value.get_running_by_pak_slot.return_value = None
    verification_steps.return_value.get_by_session_and_step_no.return_value = None
    return verification_sessions, verification_steps, kg


def _service() -> VerificationManagementService:
    return VerificationManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()),
    )


@pytest.mark.unit
async def test_open_session_creates_running_session_and_marks_kg_testing(
    repositories: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    session_repository, _, kg_repository = repositories
    pak = _pak()
    kg = _kg()
    created = _verification_session(pak)
    kg_repository.return_value.get_by_dev_eui.return_value = kg
    session_repository.return_value.create.return_value = created

    result = await _service().open_session(
        pak=pak,
        kg_dev_eui=kg.dev_eui,
        slot_no=1,
        firmware_version="1.2.3",
        total_steps=2,
    )

    assert result is created
    session_repository.return_value.lock_session_open.assert_awaited_once_with(
        kg_dev_eui=kg.dev_eui,
        pak_id=pak.id,
        slot_no=1,
    )
    session_repository.return_value.create.assert_awaited_once_with(
        kg_dev_eui=kg.dev_eui,
        pak_id=pak.id,
        slot_no=1,
        firmware_version="1.2.3",
        total_steps=2,
    )
    kg_repository.return_value.update_status.assert_awaited_once_with(
        kg,
        status=KgStatus.TESTING,
    )


@pytest.mark.unit
async def test_open_session_retries_at_the_same_location_without_creating_duplicate(
    repositories: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    session_repository, _, kg_repository = repositories
    pak = _pak()
    kg_repository.return_value.get_by_dev_eui.return_value = _kg()
    running = _verification_session(pak)
    session_repository.return_value.get_running_by_kg.return_value = running

    result = await _service().open_session(
        pak=pak,
        kg_dev_eui=running.kg_dev_eui,
        slot_no=running.slot_no,
        firmware_version="1.2.3",
        total_steps=2,
    )

    assert result is running
    session_repository.return_value.touch_activity.assert_awaited_once()
    session_repository.return_value.create.assert_not_awaited()
    kg_repository.return_value.update_status.assert_not_awaited()


@pytest.mark.unit
async def test_open_session_rejects_active_session_at_another_location(
    repositories: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    session_repository, _, kg_repository = repositories
    pak = _pak()
    kg_repository.return_value.get_by_dev_eui.return_value = _kg()
    running = _verification_session(_pak())
    session_repository.return_value.get_running_by_kg.return_value = running

    with pytest.raises(VerificationSessionAlreadyRunningError):
        await _service().open_session(
            pak=pak,
            kg_dev_eui=running.kg_dev_eui,
            slot_no=1,
            firmware_version="1.2.3",
            total_steps=2,
        )

    session_repository.return_value.create.assert_not_awaited()


@pytest.mark.unit
async def test_open_session_closes_stale_run_before_reopening(
    repositories: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    session_repository, step_repository, kg_repository = repositories
    pak = _pak()
    kg = _kg()
    stale = _verification_session(
        pak,
        last_activity_at=datetime.now(UTC) - timedelta(minutes=60),
    )
    created = _verification_session(pak)
    kg_repository.return_value.get_by_dev_eui.return_value = kg
    session_repository.return_value.get_running_by_kg.return_value = stale
    session_repository.return_value.create.return_value = created
    step_repository.return_value.get_running_by_session_for_update.return_value = None

    result = await _service().open_session(
        pak=pak,
        kg_dev_eui=kg.dev_eui,
        slot_no=1,
        firmware_version="1.2.3",
        total_steps=2,
    )

    assert result is created
    session_repository.return_value.complete.assert_awaited_once_with(
        stale,
        status=VerificationSessionStatus.INCOMPLETE,
        completed_at=ANY,
    )
    kg_repository.return_value.update_status.assert_awaited_with(kg, status=KgStatus.TESTING)


@pytest.mark.unit
async def test_start_step_rejects_parallel_running_step(
    repositories: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    session_repository, step_repository, _ = repositories
    pak = _pak()
    verification_session = _verification_session(pak)
    session_repository.return_value.get_by_id_for_update.return_value = verification_session
    step_repository.return_value.exists_running_by_session.return_value = True

    with pytest.raises(VerificationStepInProgressError):
        await _service().start_step(
            pak=pak,
            session_id=verification_session.id,
            step_no=1,
            test_name="voltage",
            test_label="Supply voltage",
            error_group_code="POWER",
        )

    step_repository.return_value.create.assert_not_awaited()


@pytest.mark.unit
async def test_start_step_records_observed_catalog_references(
    repositories: tuple[MagicMock, MagicMock, MagicMock],
    mocker: MockerFixture,
) -> None:
    session_repository, step_repository, _ = repositories
    pak = _pak()
    verification_session = _verification_session(pak)
    pak_test = SimpleNamespace(id=uuid4(), defect_group_id=uuid4())
    step = _step(verification_session)
    service = _service()
    observe_in_session = mocker.patch.object(
        service._pak_test_catalog,
        "observe_in_session",
        new_callable=AsyncMock,
        return_value=pak_test,
    )
    session_repository.return_value.get_by_id_for_update.return_value = verification_session
    step_repository.return_value.exists_running_by_session.return_value = False
    step_repository.return_value.create.return_value = step

    result = await service.start_step(
        pak=pak,
        session_id=verification_session.id,
        step_no=1,
        test_name="voltage",
        test_label="Supply voltage",
        error_group_code="POWER",
    )

    assert result is step
    observe_in_session.assert_awaited_once_with(
        ANY,
        pak=pak,
        test_name="voltage",
        test_label="Supply voltage",
        defect_group_code="POWER",
        seen_at=ANY,
    )
    step_repository.return_value.create.assert_awaited_once_with(
        session_id=verification_session.id,
        step_no=1,
        pak_test_id=pak_test.id,
        defect_group_id=pak_test.defect_group_id,
        test_name="voltage",
        test_label="Supply voltage",
        error_group_code="POWER",
    )


@pytest.mark.unit
async def test_complete_step_is_idempotent_only_for_the_same_measurement(
    repositories: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    session_repository, step_repository, _ = repositories
    pak = _pak()
    verification_session = _verification_session(pak)
    step = _step(verification_session, status=VerificationStepStatus.PASSED)
    step.measurement_value = 12.0
    step.measurement_min_value = 11.5
    step.measurement_max_value = 12.5
    step.measurement_unit = "V"
    session_repository.return_value.get_by_id_for_update.return_value = verification_session
    step_repository.return_value.get_by_session_and_step_no_for_update.return_value = step

    result = await _service().complete_step(
        pak=pak,
        session_id=verification_session.id,
        step_no=1,
        status=VerificationStepStatus.PASSED,
        measurement_value=12.0,
        measurement_min_value=11.5,
        measurement_max_value=12.5,
        measurement_unit="V",
    )

    assert result is step
    step_repository.return_value.complete.assert_not_awaited()
    session_repository.return_value.touch_activity.assert_awaited_once()

    with pytest.raises(VerificationStepAlreadyCompletedError):
        await _service().complete_step(
            pak=pak,
            session_id=verification_session.id,
            step_no=1,
            status=VerificationStepStatus.PASSED,
            measurement_value=11.0,
            measurement_min_value=11.5,
            measurement_max_value=12.5,
            measurement_unit="V",
        )


@pytest.mark.unit
async def test_complete_session_passed_requires_every_step_to_pass(
    repositories: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    session_repository, step_repository, _ = repositories
    pak = _pak()
    verification_session = _verification_session(pak, total_steps=2)
    session_repository.return_value.get_by_id_for_update.return_value = verification_session
    step_repository.return_value.get_running_by_session_for_update.return_value = None
    step_repository.return_value.count_by_session_and_status.return_value = 1

    with pytest.raises(VerificationSessionIncompleteError):
        await _service().complete_session(
            pak=pak,
            session_id=verification_session.id,
            status=VerificationSessionStatus.PASSED,
        )

    session_repository.return_value.complete.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("status", "expected_kg_status"),
    [
        pytest.param(VerificationSessionStatus.PASSED, KgStatus.READY_FOR_PACKING, id="passed"),
        pytest.param(VerificationSessionStatus.FAILED, KgStatus.TEST_FAILED, id="failed"),
        pytest.param(VerificationSessionStatus.ABORTED, KgStatus.READY_FOR_RETEST, id="aborted"),
    ],
)
async def test_complete_session_updates_kg_status(
    repositories: tuple[MagicMock, MagicMock, MagicMock],
    status: VerificationSessionStatus,
    expected_kg_status: KgStatus,
) -> None:
    session_repository, step_repository, kg_repository = repositories
    pak = _pak()
    kg = _kg(status=KgStatus.TESTING)
    verification_session = _verification_session(pak, total_steps=1)
    session_repository.return_value.get_by_id_for_update.return_value = verification_session
    step_repository.return_value.get_running_by_session_for_update.return_value = None
    step_repository.return_value.count_by_session_and_status.return_value = 1
    kg_repository.return_value.get_by_dev_eui.return_value = kg
    session_repository.return_value.complete.return_value = verification_session

    result = await _service().complete_session(
        pak=pak,
        session_id=verification_session.id,
        status=status,
    )

    assert result is verification_session
    kg_repository.return_value.update_status.assert_awaited_once_with(kg, status=expected_kg_status)


@pytest.mark.unit
async def test_expire_stale_sessions_closes_run_and_aborts_active_step(
    repositories: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    session_repository, step_repository, kg_repository = repositories
    pak = _pak()
    verification_session = _verification_session(pak)
    step = _step(verification_session)
    kg = _kg(status=KgStatus.TESTING)
    session_repository.return_value.list_stale_running_for_update.side_effect = [
        [verification_session],
    ]
    step_repository.return_value.get_running_by_session_for_update.return_value = step
    kg_repository.return_value.get_by_dev_eui.return_value = kg

    expired = await _service().expire_stale_sessions(batch_size=2)

    assert expired == 1
    step_repository.return_value.complete.assert_awaited_once_with(
        step,
        status=VerificationStepStatus.ABORTED,
        measurement_value=None,
        measurement_min_value=None,
        measurement_max_value=None,
        measurement_unit=None,
        completed_at=ANY,
    )
    session_repository.return_value.complete.assert_awaited_once_with(
        verification_session,
        status=VerificationSessionStatus.INCOMPLETE,
        completed_at=ANY,
    )
    kg_repository.return_value.update_status.assert_awaited_once_with(
        kg,
        status=KgStatus.READY_FOR_RETEST,
    )
