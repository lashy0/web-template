"""PostgreSQL characterization of quality-owned verification concurrency."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.contexts.production.batches.model import Batch, BatchStatus
from app.contexts.production.compat.verification_kg import ProductionVerificationKgAdapter
from app.contexts.production.kg.model import KgDevEuiPrefix, KgState, KgUnit
from app.contexts.quality.defects.model import DefectGroup
from app.contexts.quality.tests.model import PakTest
from app.contexts.quality.verification.commands.reconcile import (
    ReconcileStaleVerificationSessions,
)
from app.contexts.quality.verification.commands.start import StartVerificationSession
from app.contexts.quality.verification.exceptions import VerificationSessionAlreadyRunningError
from app.contexts.quality.verification.model import VerificationSession, VerificationSessionStatus
from app.contexts.quality.verification.repository import VerificationRepository
from app.modules.pak.compat.verification import LegacyVerificationPakAdapter
from app.modules.pak.models import PakDevice, PakDeviceKind
from app.shared.uow import transaction

pytestmark = pytest.mark.integration


async def make_batch(session: AsyncSession) -> Batch:
    suffix = uuid4().hex
    prefix = KgDevEuiPrefix(prefix=suffix[:10], short_code=f"kg{suffix[:6]}", name=None)
    batch = Batch(
        name="Verification migration",
        description=None,
        planned_qty=2,
        day_plan_qty=1,
        status=BatchStatus.IN_PRODUCTION,
        dev_eui_prefix=prefix.prefix,
        created_by_user_id=None,
    )
    session.add_all([prefix, batch])
    await session.flush()
    return batch


async def make_kg(session: AsyncSession, batch_id: UUID) -> KgUnit:
    value = uuid4().hex[:16]
    item = KgUnit(
        dev_eui=value, short_id=f"kg-{value[-6:]}", batch_id=batch_id, state=KgState.REGISTERED
    )
    session.add(item)
    await session.flush()
    return item


async def make_pak(session: AsyncSession) -> PakDevice:
    suffix = uuid4().hex
    item = PakDevice(
        code=f"PAK-{suffix}",
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id=f"pak-{suffix}",
        encrypted_access_key="ciphertext",
        is_active=True,
    )
    session.add(item)
    await session.flush()
    return item


async def start(
    factory: async_sessionmaker[AsyncSession], pak: PakDevice, kg_dev_eui: str, slot_no: int
) -> VerificationSession:
    async with transaction(factory) as session:
        return await StartVerificationSession(
            VerificationRepository(session),
            ProductionVerificationKgAdapter(session),
            reopen_inactivity=timedelta(minutes=60),
        ).execute(
            pak=LegacyVerificationPakAdapter(pak),
            kg_dev_eui=kg_dev_eui,
            slot_no=slot_no,
            firmware_version="1.0",
            total_steps=1,
        )


@pytest.fixture
async def scenario(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> tuple[async_sessionmaker[AsyncSession], KgUnit, KgUnit, PakDevice, PakDevice]:
    async with transaction(database_session_factory) as session:
        batch = await make_batch(session)
        first, second = await make_kg(session, batch.id), await make_kg(session, batch.id)
        first_pak, second_pak = await make_pak(session), await make_pak(session)
    return database_session_factory, first, second, first_pak, second_pak


async def running_count(
    session: AsyncSession,
    *,
    kg: str | None = None,
    pak: UUID | None = None,
    slot: int | None = None,
) -> int:
    predicates = [VerificationSession.status == VerificationSessionStatus.RUNNING]
    if kg is not None:
        predicates.append(VerificationSession.kg_dev_eui == kg)
    if pak is not None:
        predicates.append(VerificationSession.pak_id == pak)
    if slot is not None:
        predicates.append(VerificationSession.slot_no == slot)
    return int(
        await session.scalar(
            select(func.count()).select_from(VerificationSession).where(*predicates)
        )
        or 0
    )


async def test_concurrent_start_same_kg_leaves_one_running(scenario) -> None:
    factory, first, _, pak, other_pak = scenario
    results = await asyncio.gather(
        start(factory, pak, first.dev_eui, 1),
        start(factory, other_pak, first.dev_eui, 1),
        return_exceptions=True,
    )
    assert sum(isinstance(item, VerificationSession) for item in results) == 1
    assert sum(isinstance(item, VerificationSessionAlreadyRunningError) for item in results) == 1
    async with factory() as session:
        assert await running_count(session, kg=first.dev_eui) == 1


async def test_concurrent_start_same_pak_slot_leaves_one_running(scenario) -> None:
    factory, first, second, pak, _ = scenario
    await asyncio.gather(
        start(factory, pak, first.dev_eui, 1), start(factory, pak, second.dev_eui, 1)
    )
    async with factory() as session:
        assert await running_count(session, pak=pak.id, slot=1) == 1


async def test_different_kg_and_slots_start_independently(scenario) -> None:
    factory, first, second, pak, _ = scenario
    await asyncio.gather(
        start(factory, pak, first.dev_eui, 1), start(factory, pak, second.dev_eui, 2)
    )
    async with factory() as session:
        assert await running_count(session) == 2


async def test_partial_indexes_and_step_number_constraint_are_real(
    db_session: AsyncSession,
) -> None:
    batch = await make_batch(db_session)
    kg, second_kg, pak = (
        await make_kg(db_session, batch.id),
        await make_kg(db_session, batch.id),
        await make_pak(db_session),
    )
    repo = VerificationRepository(db_session)
    first = await repo.create_session(
        kg_dev_eui=kg.dev_eui, pak_id=pak.id, slot_no=1, firmware_version="1.0", total_steps=1
    )
    with pytest.raises(IntegrityError), db_session.begin_nested():
        await repo.create_session(
            kg_dev_eui=second_kg.dev_eui,
            pak_id=pak.id,
            slot_no=1,
            firmware_version="1.0",
            total_steps=1,
        )
    group = DefectGroup(code=f"G{uuid4().hex[:8]}", name="Group", description=None)
    db_session.add(group)
    await db_session.flush()
    test = PakTest(
        test_name=f"test-{uuid4().hex}",
        test_label="Test",
        defect_group_id=group.id,
        last_seen_at=datetime.now(UTC),
    )
    db_session.add(test)
    await db_session.flush()
    await repo.create_step(
        session_id=first.id,
        step_no=1,
        pak_test_id=test.id,
        defect_group_id=group.id,
        test_name=test.test_name,
        test_label=test.test_label,
        error_group_code=group.code,
    )
    with pytest.raises(IntegrityError), db_session.begin_nested():
        await repo.create_step(
            session_id=first.id,
            step_no=1,
            pak_test_id=test.id,
            defect_group_id=group.id,
            test_name=test.test_name,
            test_label=test.test_label,
            error_group_code=group.code,
        )


async def test_stale_claim_uses_skip_locked_between_workers(scenario) -> None:
    factory, first, _, pak, _ = scenario
    item = await start(factory, pak, first.dev_eui, 1)
    async with transaction(factory) as session:
        item = await VerificationRepository(session).get_session(item.id, for_update=True)
        assert item is not None
        item.last_activity_at = datetime.now(UTC) - timedelta(hours=3)
    async with factory() as first_worker, first_worker.begin():
        first_claim = await ReconcileStaleVerificationSessions(
            VerificationRepository(first_worker), session_ttl=timedelta(hours=2)
        ).execute(batch_size=10)
        assert first_claim == 1
        async with transaction(factory) as second_worker:
            second_claim = await ReconcileStaleVerificationSessions(
                VerificationRepository(second_worker), session_ttl=timedelta(hours=2)
            ).execute(batch_size=10)
            assert second_claim == 0
