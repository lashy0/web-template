"""Verification session service integration tests against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select, update

from app.db import models as m
from app.db.enums import (
    BatchStatus,
    KgOtkStatus,
    KgState,
    PakDeviceKind,
    VerificationSessionStatus,
    VerificationStepStatus,
)
from app.domain.quality.exceptions import (
    VerificationBatchArchivedError,
    VerificationKgNotFoundError,
    VerificationKgPackedError,
    VerificationKgScrappedError,
    VerificationSessionAlreadyRunningError,
    VerificationSessionIncompleteError,
    VerificationSessionNotFoundError,
    VerificationSessionNotRunningError,
    VerificationStepAlreadyCompletedError,
    VerificationStepAlreadyExistsError,
    VerificationStepInProgressError,
    VerificationStepNotFoundError,
    VerificationStepOutOfRangeError,
)
from app.domain.quality.schemas import (
    VerificationSessionComplete,
    VerificationSessionOpen,
    VerificationSessionResult,
    VerificationStepComplete,
    VerificationStepResult,
    VerificationStepStart,
)
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.quality.services import PakCheckService, VerificationSessionService
    from tests.integration.quality.conftest import CreateBatch, CreateGroup, CreatePak

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]

REOPEN = timedelta(minutes=60)


def _open(dev_eui: str, slot_no: int = 1, total_steps: int = 2) -> VerificationSessionOpen:
    return VerificationSessionOpen(
        dev_eui=dev_eui,
        slot_no=slot_no,
        firmware_version="1.0.0",
        total_steps=total_steps,
    )


def _start(
    step_no: int = 1,
    check_name: str = "rf_power",
    defect_group_code: str = "RF",
) -> VerificationStepStart:
    return VerificationStepStart(
        step_no=step_no,
        check_name=check_name,
        check_label="RF power",
        defect_group_code=defect_group_code,
    )


def _passed(value: float | None = None) -> VerificationStepComplete:
    return VerificationStepComplete(status=VerificationStepResult.PASSED, measurement_value=value)


async def _open_session(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak: m.PakDevice,
    dev_eui: str,
    slot_no: int = 1,
    total_steps: int = 2,
) -> m.VerificationSession:
    async with unit_of_work(session):
        return await verification_service.open_session(
            pak,
            _open(dev_eui, slot_no, total_steps),
            reopen_inactivity=REOPEN,
        )


async def _run_step(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    pak: m.PakDevice,
    item: m.VerificationSession,
    step_no: int,
) -> None:
    async with unit_of_work(session):
        await verification_service.start_step(
            pak, item.id, _start(step_no, f"check_{step_no}"), checks=pak_check_service
        )
        await verification_service.complete_step(pak, item.id, step_no, _passed())


async def _complete(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak: m.PakDevice,
    item: m.VerificationSession,
    result: VerificationSessionResult,
) -> m.VerificationSession:
    async with unit_of_work(session):
        return await verification_service.complete_session(
            pak, item.id, VerificationSessionComplete(status=result),
        )


async def _kg(session: AsyncSession, dev_eui: str) -> m.KgUnit:
    session.expire_all()
    kg = await session.get(m.KgUnit, dev_eui)
    assert kg is not None

    return kg


async def test_open_session_starts_running_session_of_the_batch(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak(PakDeviceKind.ENGINEERING)

    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    assert (item.status, item.batch_id, item.pak_kind) == (
        VerificationSessionStatus.RUNNING,
        batch.id,
        PakDeviceKind.ENGINEERING,
    )


async def test_open_session_for_unknown_kg_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_pak: CreatePak,
) -> None:
    pak = await create_pak()

    with pytest.raises(VerificationKgNotFoundError):
        await _open_session(session, verification_service, pak, "ffffffffffffffff")


async def test_open_session_for_scrapped_kg_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()

    async with unit_of_work(session):
        await session.execute(
            update(m.KgUnit)
            .where(m.KgUnit.dev_eui == batch.first_dev_eui)
            .values(state=KgState.SCRAPPED),
        )

    with pytest.raises(VerificationKgScrappedError):
        await _open_session(session, verification_service, pak, batch.first_dev_eui)


async def test_open_session_for_packed_kg_on_otk_line_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak(PakDeviceKind.OTK_LINE)

    async with unit_of_work(session):
        await session.execute(
            update(m.KgUnit)
            .where(m.KgUnit.dev_eui == batch.first_dev_eui)
            .values(state=KgState.PACKED, packed_at=datetime.now(UTC)),
        )

    with pytest.raises(VerificationKgPackedError):
        await _open_session(session, verification_service, pak, batch.first_dev_eui)


async def test_open_session_for_packed_kg_on_engineering_pak_starts_it(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak(PakDeviceKind.ENGINEERING)

    async with unit_of_work(session):
        await session.execute(
            update(m.KgUnit)
            .where(m.KgUnit.dev_eui == batch.first_dev_eui)
            .values(state=KgState.PACKED, packed_at=datetime.now(UTC)),
        )

    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    assert item.status is VerificationSessionStatus.RUNNING


async def test_open_session_for_kg_of_archived_batch_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch(archived=True)
    pak = await create_pak()

    with pytest.raises(VerificationBatchArchivedError):
        await _open_session(session, verification_service, pak, batch.first_dev_eui)


async def test_open_session_for_kg_of_completed_batch_is_allowed(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch(status=BatchStatus.COMPLETED)
    pak = await create_pak()

    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    assert item.status is VerificationSessionStatus.RUNNING


async def test_open_session_again_in_the_same_slot_resumes_it(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    first = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    again = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    assert again.id == first.id


async def test_open_session_in_another_slot_while_running_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    await _open_session(
        session,
        verification_service,
        pak,
        batch.first_dev_eui,
        slot_no=1,
    )

    with pytest.raises(VerificationSessionAlreadyRunningError):
        await _open_session(
            session,
            verification_service,
            pak,
            batch.first_dev_eui,
            slot_no=2,
        )


async def test_open_session_elsewhere_after_inactivity_closes_the_idle_one(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    idle = await _open_session(
        session,
        verification_service,
        pak,
        batch.first_dev_eui,
        slot_no=1,
    )

    async with unit_of_work(session):
        await verification_service.open_session(
            pak,
            _open(batch.first_dev_eui, slot_no=2),
            reopen_inactivity=timedelta(0),
        )

    assert idle.status is VerificationSessionStatus.INCOMPLETE


async def test_open_session_in_an_occupied_slot_closes_the_previous_kg_session(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    previous = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    await _open_session(session, verification_service, pak, batch.last_dev_eui)

    assert previous.status is VerificationSessionStatus.INCOMPLETE


async def test_start_step_links_the_check_and_its_defect_group(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
    create_group: CreateGroup,
) -> None:
    group = await create_group("RF")
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    async with unit_of_work(session):
        step, observation = await verification_service.start_step(
            pak, item.id, _start(), checks=pak_check_service,
        )

    assert observation is not None
    assert (step.status, step.check_id, step.defect_group_id) == (
        VerificationStepStatus.RUNNING,
        observation.check.id,
        group.id,
    )


async def test_start_step_with_unknown_defect_group_is_accepted_without_a_group(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    async with unit_of_work(session):
        step, _ = await verification_service.start_step(
            pak,
            item.id,
            _start(defect_group_code="UNKNOWN"),
            checks=pak_check_service,
        )

    assert (step.defect_group_code, step.defect_group_id) == ("UNKNOWN", None)


async def test_start_step_again_returns_the_step_without_observing_the_check(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    async with unit_of_work(session):
        first, _ = await verification_service.start_step(
            pak, item.id, _start(), checks=pak_check_service,
        )

    async with unit_of_work(session):
        again, observation = await verification_service.start_step(
            pak, item.id, _start(), checks=pak_check_service,
        )

    assert (again.id, observation) == (first.id, None)


async def test_start_step_number_again_with_another_check_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    async with unit_of_work(session):
        await verification_service.start_step(pak, item.id, _start(), checks=pak_check_service)

    with pytest.raises(VerificationStepAlreadyExistsError):
        async with unit_of_work(session):
            await verification_service.start_step(
                pak,
                item.id,
                _start(check_name="battery"),
                checks=pak_check_service,
            )


async def test_start_step_while_another_runs_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    async with unit_of_work(session):
        await verification_service.start_step(pak, item.id, _start(1), checks=pak_check_service)

    with pytest.raises(VerificationStepInProgressError):
        async with unit_of_work(session):
            await verification_service.start_step(
                pak, item.id, _start(2, "battery"), checks=pak_check_service,
            )


async def test_start_step_beyond_total_steps_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui, total_steps=1)

    with pytest.raises(VerificationStepOutOfRangeError):
        async with unit_of_work(session):
            await verification_service.start_step(
                pak, item.id, _start(2), checks=pak_check_service,
            )


async def test_start_step_in_another_paks_session_is_not_found(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    owner = await create_pak()
    other = await create_pak()
    item = await _open_session(session, verification_service, owner, batch.first_dev_eui)

    with pytest.raises(VerificationSessionNotFoundError):
        async with unit_of_work(session):
            await verification_service.start_step(other, item.id, _start(), checks=pak_check_service)


async def test_start_step_in_finished_session_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)
    await _complete(session, verification_service, pak, item, VerificationSessionResult.FAILED)

    with pytest.raises(VerificationSessionNotRunningError):
        async with unit_of_work(session):
            await verification_service.start_step(pak, item.id, _start(), checks=pak_check_service)


async def test_complete_step_records_the_result(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    async with unit_of_work(session):
        await verification_service.start_step(pak, item.id, _start(), checks=pak_check_service)
        step = await verification_service.complete_step(pak, item.id, 1, _passed(12.5))

    assert (step.status, step.measurement_value, step.completed_at is not None) == (
        VerificationStepStatus.PASSED,
        12.5,
        True,
    )


async def test_complete_step_again_with_the_same_result_returns_it(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)
    await _run_step(session, verification_service, pak_check_service, pak, item, 1)

    async with unit_of_work(session):
        step = await verification_service.complete_step(pak, item.id, 1, _passed())

    assert step.status is VerificationStepStatus.PASSED


async def test_complete_step_again_with_another_result_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)
    await _run_step(session, verification_service, pak_check_service, pak, item, 1)

    with pytest.raises(VerificationStepAlreadyCompletedError):
        async with unit_of_work(session):
            await verification_service.complete_step(
                pak,
                item.id,
                1,
                VerificationStepComplete(status=VerificationStepResult.FAILED),
            )


async def test_complete_step_not_started_is_not_found(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    with pytest.raises(VerificationStepNotFoundError):
        async with unit_of_work(session):
            await verification_service.complete_step(pak, item.id, 1, _passed())


async def test_passed_session_on_otk_line_pak_passes_the_kg(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak(PakDeviceKind.OTK_LINE)
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui, total_steps=1)
    await _run_step(session, verification_service, pak_check_service, pak, item, 1)

    await _complete(session, verification_service, pak, item, VerificationSessionResult.PASSED)

    kg = await _kg(session, batch.first_dev_eui)
    assert (kg.otk_status, kg.last_verification_at is not None) == (KgOtkStatus.PASSED, True)


async def test_failed_session_on_otk_line_pak_fails_the_kg(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak(PakDeviceKind.OTK_LINE)
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    await _complete(session, verification_service, pak, item, VerificationSessionResult.FAILED)

    assert (await _kg(session, batch.first_dev_eui)).otk_status is KgOtkStatus.FAILED


async def test_passed_session_on_engineering_pak_leaves_the_kg_status(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak(PakDeviceKind.ENGINEERING)
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui, total_steps=1)
    await _run_step(session, verification_service, pak_check_service, pak, item, 1)

    await _complete(session, verification_service, pak, item, VerificationSessionResult.PASSED)

    assert (await _kg(session, batch.first_dev_eui)).otk_status is KgOtkStatus.NOT_VERIFIED


async def test_aborted_session_on_otk_line_pak_leaves_the_kg_status(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak(PakDeviceKind.OTK_LINE)
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    await _complete(session, verification_service, pak, item, VerificationSessionResult.ABORTED)

    assert (await _kg(session, batch.first_dev_eui)).otk_status is KgOtkStatus.NOT_VERIFIED


async def test_pass_session_with_steps_left_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui, total_steps=2)
    await _run_step(session, verification_service, pak_check_service, pak, item, 1)

    with pytest.raises(VerificationSessionIncompleteError):
        await _complete(session, verification_service, pak, item, VerificationSessionResult.PASSED)


async def test_fail_session_with_a_running_step_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    async with unit_of_work(session):
        await verification_service.start_step(pak, item.id, _start(), checks=pak_check_service)

    with pytest.raises(VerificationSessionIncompleteError):
        await _complete(session, verification_service, pak, item, VerificationSessionResult.FAILED)


async def test_abort_session_aborts_its_running_step(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    async with unit_of_work(session):
        step, _ = await verification_service.start_step(pak, item.id, _start(), checks=pak_check_service)

    await _complete(session, verification_service, pak, item, VerificationSessionResult.ABORTED)

    assert step.status is VerificationStepStatus.ABORTED


async def test_complete_session_again_with_the_same_result_returns_it(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)
    await _complete(session, verification_service, pak, item, VerificationSessionResult.FAILED)

    again = await _complete(session, verification_service, pak, item, VerificationSessionResult.FAILED)

    assert again.status is VerificationSessionStatus.FAILED


async def test_complete_finished_session_with_another_result_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)
    await _complete(session, verification_service, pak, item, VerificationSessionResult.FAILED)

    with pytest.raises(VerificationSessionNotRunningError):
        await _complete(session, verification_service, pak, item, VerificationSessionResult.ABORTED)


async def test_abort_session_the_system_closed_as_incomplete_returns_it(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    async with unit_of_work(session):
        await verification_service.expire_stale(idle_for=timedelta(0), limit=10)

    closed = await _complete(session, verification_service, pak, item, VerificationSessionResult.ABORTED)

    assert closed.status is VerificationSessionStatus.INCOMPLETE


async def test_finish_session_the_system_closed_as_incomplete_is_rejected(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    async with unit_of_work(session):
        await verification_service.expire_stale(idle_for=timedelta(0), limit=10)

    with pytest.raises(VerificationSessionNotRunningError):
        await _complete(session, verification_service, pak, item, VerificationSessionResult.FAILED)


async def test_complete_another_paks_session_is_not_found(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    owner = await create_pak()
    other = await create_pak()
    item = await _open_session(session, verification_service, owner, batch.first_dev_eui)

    with pytest.raises(VerificationSessionNotFoundError):
        await _complete(session, verification_service, other, item, VerificationSessionResult.FAILED)


async def test_expire_stale_closes_idle_sessions_and_their_running_steps(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)

    async with unit_of_work(session):
        step, _ = await verification_service.start_step(pak, item.id, _start(), checks=pak_check_service)

    step_id = step.id

    async with unit_of_work(session):
        expired = await verification_service.expire_stale(idle_for=timedelta(0), limit=10)

    statuses = (
        await session.execute(
            select(m.VerificationSession.status, m.VerificationStep.status)
            .join(m.VerificationStep, m.VerificationStep.session_id == m.VerificationSession.id)
            .where(m.VerificationStep.id == step_id)
        )
    ).one()
    assert (expired, *statuses) == (1, VerificationSessionStatus.INCOMPLETE, VerificationStepStatus.ABORTED)


async def test_expire_stale_keeps_recently_active_sessions(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    await _open_session(session, verification_service, pak, batch.first_dev_eui)

    async with unit_of_work(session):
        expired = await verification_service.expire_stale(idle_for=timedelta(hours=2), limit=10)

    assert expired == 0


async def test_get_with_steps_orders_steps_by_number(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    pak_check_service: PakCheckService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)
    item_id = item.id
    await _run_step(session, verification_service, pak_check_service, pak, item, 2)
    await _run_step(session, verification_service, pak_check_service, pak, item, 1)
    session.expire_all()

    stored = await verification_service.get_with_steps(item_id)

    assert [step.step_no for step in stored.steps] == [1, 2]


async def test_last_activity_is_kept_when_the_system_closes_a_session(
    session: AsyncSession,
    verification_service: VerificationSessionService,
    create_batch: CreateBatch,
    create_pak: CreatePak,
) -> None:
    batch = await create_batch()
    pak = await create_pak()
    item = await _open_session(session, verification_service, pak, batch.first_dev_eui)
    last_report = datetime.now(UTC) - timedelta(hours=3)

    async with unit_of_work(session):
        item.last_activity_at = last_report

    async with unit_of_work(session):
        await verification_service.expire_stale(idle_for=timedelta(hours=2), limit=10)

    assert item.last_activity_at == last_report
