from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch.models import Batch, BatchStatus
from app.modules.defects.repository import DefectGroupRepository
from app.modules.kg.models import KgDevEuiPrefix, KgStatus, KgUnit
from app.modules.pak.models import PakDevice, PakDeviceKind, PakTest
from app.modules.pak.repository import PakTestRepository
from app.modules.verification.models import VerificationSessionStatus
from app.modules.verification.repository import (
    VerificationSessionRepository,
    VerificationStepRepository,
)


async def _batch(session: AsyncSession) -> Batch:
    suffix = uuid4().hex
    prefix = KgDevEuiPrefix(
        prefix=suffix[:10],
        short_code=f"kg{suffix[:6]}",
        name=None,
    )
    session.add(prefix)
    await session.flush()

    batch = Batch(
        id=uuid4(),
        name="Verification test batch",
        description=None,
        dev_eui_prefix=prefix.prefix,
        planned_qty=10,
        day_plan_qty=1,
        status=BatchStatus.IN_PRODUCTION,
        created_by_user_id=None,
    )
    session.add(batch)
    await session.flush()
    return batch


async def _kg(session: AsyncSession, *, batch_id: UUID) -> KgUnit:
    suffix = uuid4().hex
    kg = KgUnit(
        dev_eui=suffix[:16],
        short_id=f"kg-{suffix[-8:]}",
        batch_id=batch_id,
        status=KgStatus.REGISTERED,
    )
    session.add(kg)
    await session.flush()
    return kg


async def _pak(session: AsyncSession) -> PakDevice:
    suffix = uuid4().hex
    pak = PakDevice(
        id=uuid4(),
        code=f"PAK-{suffix}",
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id=f"pak-{suffix}",
        encrypted_access_key="ciphertext",
        is_active=True,
    )
    session.add(pak)
    await session.flush()
    return pak


async def _pak_test(session: AsyncSession) -> tuple[PakTest, str]:
    suffix = uuid4().hex[:8]
    group = await DefectGroupRepository(session).create(
        code=f"POWER_{suffix}",
        name="Power supply",
        description=None,
    )
    return await PakTestRepository(session).create(
        test_name=f"power_{suffix}",
        test_label="Supply voltage",
        defect_group_id=group.id,
        last_seen_at=datetime.now(UTC),
    ), group.code


@pytest.mark.integration
async def test_only_one_running_session_is_allowed_per_kg(db_session: AsyncSession) -> None:
    batch = await _batch(db_session)
    kg = await _kg(db_session, batch_id=batch.id)
    pak = await _pak(db_session)
    repository = VerificationSessionRepository(db_session)
    first = await repository.create(
        kg_dev_eui=kg.dev_eui,
        pak_id=pak.id,
        slot_no=1,
        firmware_version="1.0.0",
        total_steps=2,
    )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await repository.create(
                kg_dev_eui=kg.dev_eui,
                pak_id=pak.id,
                slot_no=2,
                firmware_version="1.0.0",
                total_steps=2,
            )

    await repository.complete(
        first,
        status=VerificationSessionStatus.PASSED,
        completed_at=datetime.now(UTC),
    )
    reopened = await repository.create(
        kg_dev_eui=kg.dev_eui,
        pak_id=pak.id,
        slot_no=1,
        firmware_version="1.0.1",
        total_steps=2,
    )

    assert reopened.status is VerificationSessionStatus.RUNNING


@pytest.mark.integration
async def test_only_one_running_session_is_allowed_per_pak_slot(db_session: AsyncSession) -> None:
    batch = await _batch(db_session)
    first_kg = await _kg(db_session, batch_id=batch.id)
    second_kg = await _kg(db_session, batch_id=batch.id)
    pak = await _pak(db_session)
    repository = VerificationSessionRepository(db_session)
    await repository.create(
        kg_dev_eui=first_kg.dev_eui,
        pak_id=pak.id,
        slot_no=1,
        firmware_version="1.0.0",
        total_steps=2,
    )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await repository.create(
                kg_dev_eui=second_kg.dev_eui,
                pak_id=pak.id,
                slot_no=1,
                firmware_version="1.0.0",
                total_steps=2,
            )


@pytest.mark.integration
async def test_step_number_is_unique_within_a_verification_session(
    db_session: AsyncSession,
) -> None:
    batch = await _batch(db_session)
    first_kg = await _kg(db_session, batch_id=batch.id)
    second_kg = await _kg(db_session, batch_id=batch.id)
    pak = await _pak(db_session)
    pak_test, defect_group_code = await _pak_test(db_session)
    session_repository = VerificationSessionRepository(db_session)
    step_repository = VerificationStepRepository(db_session)
    first_session = await session_repository.create(
        kg_dev_eui=first_kg.dev_eui,
        pak_id=pak.id,
        slot_no=1,
        firmware_version="1.0.0",
        total_steps=2,
    )
    second_session = await session_repository.create(
        kg_dev_eui=second_kg.dev_eui,
        pak_id=pak.id,
        slot_no=2,
        firmware_version="1.0.0",
        total_steps=2,
    )
    await step_repository.create(
        session_id=first_session.id,
        step_no=1,
        pak_test_id=pak_test.id,
        defect_group_id=pak_test.defect_group_id,
        test_name=pak_test.test_name,
        test_label=pak_test.test_label,
        error_group_code=defect_group_code,
    )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await step_repository.create(
                session_id=first_session.id,
                step_no=1,
                pak_test_id=pak_test.id,
                defect_group_id=pak_test.defect_group_id,
                test_name="power retry",
                test_label="Supply voltage retry",
                error_group_code=defect_group_code,
            )

    allowed = await step_repository.create(
        session_id=second_session.id,
        step_no=1,
        pak_test_id=pak_test.id,
        defect_group_id=pak_test.defect_group_id,
        test_name=pak_test.test_name,
        test_label=pak_test.test_label,
        error_group_code=defect_group_code,
    )

    assert allowed.session_id == second_session.id
    assert allowed.pak_test_id == pak_test.id
    assert allowed.defect_group_id == pak_test.defect_group_id


@pytest.mark.integration
async def test_verification_existence_queries_are_scoped_to_pak_kg_and_batch(
    db_session: AsyncSession,
) -> None:
    included_batch = await _batch(db_session)
    excluded_batch = await _batch(db_session)
    included_kg = await _kg(db_session, batch_id=included_batch.id)
    excluded_kg = await _kg(db_session, batch_id=excluded_batch.id)
    included_pak = await _pak(db_session)
    excluded_pak = await _pak(db_session)
    repository = VerificationSessionRepository(db_session)
    await repository.create(
        kg_dev_eui=included_kg.dev_eui,
        pak_id=included_pak.id,
        slot_no=1,
        firmware_version="1.0.0",
        total_steps=2,
    )
    await repository.create(
        kg_dev_eui=excluded_kg.dev_eui,
        pak_id=excluded_pak.id,
        slot_no=1,
        firmware_version="1.0.0",
        total_steps=2,
    )

    assert await repository.exists_by_pak_id(included_pak.id)
    assert not await repository.exists_by_pak_id(uuid4())
    assert await repository.exists_by_kg_dev_eui(included_kg.dev_eui)
    assert not await repository.exists_by_kg_dev_eui(uuid4().hex[:16])
    assert await repository.exists_by_batch_id(included_batch.id)
    assert not await repository.exists_by_batch_id(uuid4())
