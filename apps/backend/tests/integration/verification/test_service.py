import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.audit.models import AuditEvent
from app.modules.kg.models import KgStatus, KgUnit
from app.modules.kg.repositories import KgRepository
from app.modules.kg.services import KgManagementService
from app.modules.verification.exceptions import (
    VerificationKgNotReadyError,
    VerificationSessionAlreadyRunningError,
)
from app.modules.verification.models import (
    VerificationSession,
    VerificationSessionStatus,
    VerificationStepStatus,
)
from app.modules.verification.repositories import VerificationSessionRepository
from app.modules.verification.services import (
    VerificationManagementService,
    VerificationSessionService,
)
from tests.integration.verification.test_repository import _batch, _kg, _pak, _pak_test

pytestmark = pytest.mark.integration


@pytest.fixture
async def scenario(database_session_factory):
    factory = database_session_factory
    async with factory() as session, session.begin():
        batch = await _batch(session)
        kg = await _kg(session, batch_id=batch.id)
        pak = await _pak(session)
        other_pak = await _pak(session)
        test, code = await _pak_test(session)
    return factory, kg, pak, other_pak, test, code


def actor():
    return CurrentPrincipal(
        user_id=uuid4(),
        identity_id=uuid4(),
        session_id=uuid4(),
        role=Role.ADMINISTRATOR,
        name="Integration",
        login="integration",
    )


async def open_run(service, kg, pak):
    return await service.open_session(
        pak=pak, kg_dev_eui=kg.dev_eui, slot_no=1, firmware_version="1.0", total_steps=1
    )


async def test_verification_full_lifecycle_and_idempotent_retries(scenario):
    factory, kg, pak, _, test, code = scenario
    service = VerificationManagementService(factory)
    run = await open_run(service, kg, pak)
    assert (await open_run(service, kg, pak)).id == run.id
    args = {
        "pak": pak,
        "session_id": run.id,
        "step_no": 1,
        "test_name": test.test_name,
        "test_label": test.test_label,
        "error_group_code": code,
    }
    step = await service.start_step(**args)
    assert (await service.start_step(**args)).id == step.id
    result = {
        "pak": pak,
        "session_id": run.id,
        "step_no": 1,
        "status": VerificationStepStatus.PASSED,
        "measurement_value": 2.0,
        "measurement_min_value": 1.0,
        "measurement_max_value": 3.0,
        "measurement_unit": "V",
    }
    await service.complete_step(**result)
    assert (await service.complete_step(**result)).id == step.id
    await service.complete_session(
        pak=pak, session_id=run.id, status=VerificationSessionStatus.PASSED
    )
    assert (
        await service.complete_session(
            pak=pak, session_id=run.id, status=VerificationSessionStatus.PASSED
        )
    ).id == run.id
    assert (await KgManagementService(factory).get(kg.dev_eui)).status == KgStatus.READY_FOR_PACKING


async def test_parallel_open_allows_only_one_active_location(scenario):
    factory, kg, pak, other_pak, _, _ = scenario
    service = VerificationManagementService(factory)
    results = await asyncio.gather(
        open_run(service, kg, pak), open_run(service, kg, other_pak), return_exceptions=True
    )
    assert sum(isinstance(item, VerificationSession) for item in results) == 1
    assert sum(isinstance(item, VerificationSessionAlreadyRunningError) for item in results) == 1
    async with factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(VerificationSession)
                .where(
                    VerificationSession.kg_dev_eui == kg.dev_eui,
                    VerificationSession.status == VerificationSessionStatus.RUNNING,
                )
            )
            == 1
        )


async def wait_for_blocked_task(factory, task, pid_holder):
    async def blocked():
        async with factory() as session:
            while not pid_holder or not await session.scalar(
                select(func.pg_blocking_pids(pid_holder[0]))
            ):
                if task.done():
                    task.result()
                    raise AssertionError("Operation did not wait for the KG row lock")
                await asyncio.sleep(0.01)

    await asyncio.wait_for(blocked(), 5)


@pytest.mark.parametrize("operation", ["complete", "expire"])
async def test_concurrent_admin_correction_is_not_overwritten(scenario, monkeypatch, operation):
    factory, kg, pak, _, _, _ = scenario
    service = VerificationManagementService(factory)
    run = await open_run(service, kg, pak)
    if operation == "expire":
        async with factory() as session, session.begin():
            await session.execute(
                update(VerificationSession)
                .where(VerificationSession.id == run.id)
                .values(last_activity_at=datetime.now(UTC) - timedelta(hours=3))
            )
    pid_holder = []
    original = KgRepository.get_by_dev_eui

    async def observed_get(repository, dev_eui, *, for_update=False):
        if for_update:
            pid_holder.append(await repository._session.scalar(select(func.pg_backend_pid())))
        return await original(repository, dev_eui, for_update=for_update)

    original_many = KgRepository.get_many_by_dev_euis

    async def observed_many(repository, dev_euis, *, for_update=False):
        if for_update:
            pid_holder.append(await repository._session.scalar(select(func.pg_backend_pid())))
        return await original_many(repository, dev_euis, for_update=for_update)

    monkeypatch.setattr(KgRepository, "get_many_by_dev_euis", observed_many)

    async with factory() as owner:
        async with owner.begin():
            locked = await original(KgRepository(owner), kg.dev_eui, for_update=True)
            monkeypatch.setattr(KgRepository, "get_by_dev_eui", observed_get)
            task = asyncio.create_task(
                service.complete_session(
                    pak=pak, session_id=run.id, status=VerificationSessionStatus.ABORTED
                )
                if operation == "complete"
                else service.expire_stale_sessions()
            )
            try:
                await wait_for_blocked_task(factory, task, pid_holder)
                await KgRepository(owner).update_status(locked, status=KgStatus.PACKED)
            except BaseException:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                raise
    if operation == "complete":
        with pytest.raises(VerificationKgNotReadyError):
            await task
    else:
        assert await task >= 1
    async with factory() as session:
        assert (await session.get(KgUnit, kg.dev_eui)).status == KgStatus.PACKED
        assert (await session.get(VerificationSession, run.id)).status == (
            VerificationSessionStatus.RUNNING
            if operation == "complete"
            else VerificationSessionStatus.INCOMPLETE
        )


async def test_manual_status_change_reads_locked_state_for_audit(scenario, monkeypatch):
    factory, kg, _, _, _, _ = scenario
    pid_holder = []
    original = KgRepository.get_by_dev_eui

    async def observed_get(repository, dev_eui, *, for_update=False):
        if for_update:
            pid_holder.append(await repository._session.scalar(select(func.pg_backend_pid())))
        return await original(repository, dev_eui, for_update=for_update)

    principal = actor()
    async with factory() as owner:
        async with owner.begin():
            locked = await original(KgRepository(owner), kg.dev_eui, for_update=True)
            monkeypatch.setattr(KgRepository, "get_by_dev_eui", observed_get)
            task = asyncio.create_task(
                KgManagementService(factory).set_status(
                    actor=principal, dev_eui=kg.dev_eui, status=KgStatus.SCRAPPED
                )
            )
            try:
                await wait_for_blocked_task(factory, task, pid_holder)
                await KgRepository(owner).update_status(locked, status=KgStatus.PACKED)
            except BaseException:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                raise
    await task
    async with factory() as session:
        event = await session.scalar(
            select(AuditEvent).where(AuditEvent.actor_id == str(principal.user_id))
        )
        assert event.old_data["status"] == "PACKED"
        assert event.new_data["status"] == "SCRAPPED"


async def test_failed_completion_rolls_back_kg_and_session(scenario, monkeypatch):
    factory, kg, pak, _, _, _ = scenario
    service = VerificationManagementService(factory)
    run = await open_run(service, kg, pak)
    original = VerificationSessionRepository.complete

    async def fail_after_flush(repository, *args, **kwargs):
        await original(repository, *args, **kwargs)
        raise RuntimeError("injected persistence failure")

    monkeypatch.setattr(VerificationSessionRepository, "complete", fail_after_flush)
    with pytest.raises(RuntimeError, match="injected"):
        await service.complete_session(
            pak=pak, session_id=run.id, status=VerificationSessionStatus.ABORTED
        )
    async with factory() as session:
        assert (await session.get(KgUnit, kg.dev_eui)).status == KgStatus.TESTING
        assert (
            await session.get(VerificationSession, run.id)
        ).status == VerificationSessionStatus.RUNNING


async def test_reopen_waits_for_concurrent_completion(scenario, monkeypatch):
    factory, kg, pak, _, _, _ = scenario
    service = VerificationManagementService(factory)
    run = await open_run(service, kg, pak)
    pid_holder = []
    original = VerificationSessionRepository.lock_running_candidates

    async def observed_lock(repository, **kwargs):
        pid_holder.append(await repository._session.scalar(select(func.pg_backend_pid())))
        return await original(repository, **kwargs)

    monkeypatch.setattr(VerificationSessionRepository, "lock_running_candidates", observed_lock)
    async with factory() as owner:
        async with owner.begin():
            await VerificationSessionRepository(owner).get_by_id_for_update(run.id)
            task = asyncio.create_task(open_run(service, kg, pak))
            try:
                await wait_for_blocked_task(factory, task, pid_holder)
                await VerificationSessionService(owner).complete_session(
                    pak=pak, session_id=run.id, status=VerificationSessionStatus.ABORTED
                )
            except BaseException:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                raise
    reopened = await task
    assert reopened.id != run.id
    assert reopened.status == VerificationSessionStatus.RUNNING
    async with factory() as session:
        assert (
            await session.get(VerificationSession, run.id)
        ).status == VerificationSessionStatus.ABORTED


async def test_failed_open_rolls_back_testing_status(scenario, monkeypatch):
    factory, kg, pak, _, _, _ = scenario
    original = VerificationSessionRepository.create

    async def fail_after_flush(repository, **kwargs):
        await original(repository, **kwargs)
        raise RuntimeError("injected create failure")

    monkeypatch.setattr(VerificationSessionRepository, "create", fail_after_flush)
    with pytest.raises(RuntimeError, match="injected"):
        await open_run(VerificationManagementService(factory), kg, pak)
    async with factory() as session:
        assert (await session.get(KgUnit, kg.dev_eui)).status == KgStatus.REGISTERED
        assert (
            await session.scalar(
                select(func.count())
                .select_from(VerificationSession)
                .where(VerificationSession.kg_dev_eui == kg.dev_eui)
            )
            == 0
        )
