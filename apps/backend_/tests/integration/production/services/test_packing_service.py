"""Packing service integration tests against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from advanced_alchemy.exceptions import NotFoundError
from sqlalchemy import update

from app.db import models as m
from app.db.enums import (
    KgOtkStatus,
    KgState,
    PakDeviceKind,
    UserRole,
    VerificationSessionStatus,
)
from app.domain.production.exceptions import (
    PackingBatchArchivedError,
    PackingKgAlreadyPackedError,
    PackingKgScrappedError,
    PackingOtkInProgressError,
    PackingOtkNotPassedError,
)
from app.domain.production.schemas import PackingBlocker
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.production.services import BatchService, PackingService
    from tests.integration.production.conftest import CreateBatch, CreatePrefix

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


@pytest.fixture
async def packer(session: AsyncSession) -> m.User:
    """Commit a local packer; packing records who packed a unit."""
    user = m.User(
        identity_id=uuid4(),
        identity_login=f"packer-{uuid4().hex[:8]}",
        name="Packer",
        role=UserRole.PACKER,
    )

    async with unit_of_work(session):
        session.add(user)

    return user


async def _set_otk_status(session: AsyncSession, dev_eui: str, otk_status: KgOtkStatus) -> None:
    async with unit_of_work(session):
        await session.execute(
            update(m.KgUnit)
            .where(m.KgUnit.dev_eui == dev_eui)
            .values(otk_status=otk_status)
        )


async def _start_session(session: AsyncSession, batch: m.Batch, kind: PakDeviceKind) -> None:
    now = datetime.now(UTC)
    suffix = uuid4().hex[:8]

    async with unit_of_work(session):
        pak = m.PakDevice(
            code=f"pak-{suffix}",
            kind=kind,
            oauth_client_id=f"pak-client-{suffix}",
            encrypted_access_key="unused",
        )
        session.add(pak)
        await session.flush()
        session.add(
            m.VerificationSession(
                dev_eui=batch.first_dev_eui,
                batch_id=batch.id,
                pak_id=pak.id,
                pak_kind=kind,
                slot_no=1,
                firmware_version="1.0.0",
                total_steps=1,
                status=VerificationSessionStatus.RUNNING,
                started_at=now,
                last_activity_at=now,
            )
        )


async def _pack(
    session: AsyncSession,
    packing_service: PackingService,
    dev_eui: str,
    packer: m.User,
) -> m.KgUnit:
    async with unit_of_work(session):
        return await packing_service.pack(dev_eui, packed_by_id=packer.id)


async def test_find_unit_accepts_short_id_in_any_case(
    packing_service: PackingService,
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
) -> None:
    prefix = await create_prefix("a1b2c3d4e5", "ab1")
    batch = await create_batch(prefix)

    kg, _ = await packing_service.find_unit(" AB1-000001 ")

    assert kg.dev_eui == batch.first_dev_eui


async def test_find_unknown_unit_is_not_found(packing_service: PackingService) -> None:
    with pytest.raises(NotFoundError):
        await packing_service.find_unit("ffffffffffffffff")


async def test_find_unit_that_passed_otk_has_no_blocker(
    session: AsyncSession,
    packing_service: PackingService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()
    await _set_otk_status(session, batch.first_dev_eui, KgOtkStatus.PASSED)

    _, blocker = await packing_service.find_unit(batch.first_dev_eui)

    assert blocker is None


async def test_find_unit_not_verified_is_blocked_by_otk(
    packing_service: PackingService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    _, blocker = await packing_service.find_unit(batch.first_dev_eui)

    assert blocker is PackingBlocker.OTK_NOT_PASSED


async def test_pack_marks_unit_packed_by_user(
    session: AsyncSession,
    packing_service: PackingService,
    create_batch: CreateBatch,
    packer: m.User,
) -> None:
    batch = await create_batch()
    await _set_otk_status(session, batch.first_dev_eui, KgOtkStatus.PASSED)

    kg = await _pack(session, packing_service, batch.first_dev_eui, packer)

    assert (kg.state, kg.packed_at is not None, kg.packed_by_id) == (KgState.PACKED, True, packer.id)


async def test_pack_counts_unit_in_batch_packed_qty(
    session: AsyncSession,
    packing_service: PackingService,
    batch_service: BatchService,
    create_batch: CreateBatch,
    packer: m.User,
) -> None:
    batch = await create_batch()
    await _set_otk_status(session, batch.first_dev_eui, KgOtkStatus.PASSED)
    await _pack(session, packing_service, batch.first_dev_eui, packer)
    session.expunge_all()

    reloaded = await batch_service.get(batch.id)

    assert reloaded.packed_qty == 1


async def test_pack_unit_of_completed_batch_packs_it(
    session: AsyncSession,
    packing_service: PackingService,
    batch_service: BatchService,
    create_batch: CreateBatch,
    packer: m.User,
) -> None:
    batch = await create_batch()
    await _set_otk_status(session, batch.first_dev_eui, KgOtkStatus.PASSED)

    async with unit_of_work(session):
        await batch_service.complete_batch(batch.id)

    kg = await _pack(session, packing_service, batch.first_dev_eui, packer)

    assert kg.state is KgState.PACKED


async def test_pack_packed_unit_is_rejected(
    session: AsyncSession,
    packing_service: PackingService,
    create_batch: CreateBatch,
    packer: m.User,
) -> None:
    batch = await create_batch()
    await _set_otk_status(session, batch.first_dev_eui, KgOtkStatus.PASSED)
    await _pack(session, packing_service, batch.first_dev_eui, packer)

    with pytest.raises(PackingKgAlreadyPackedError):
        await _pack(session, packing_service, batch.first_dev_eui, packer)


async def test_pack_scrapped_unit_is_rejected(
    session: AsyncSession,
    packing_service: PackingService,
    create_batch: CreateBatch,
    packer: m.User,
) -> None:
    batch = await create_batch()

    async with unit_of_work(session):
        await session.execute(
            update(m.KgUnit)
            .where(m.KgUnit.dev_eui == batch.first_dev_eui)
            .values(state=KgState.SCRAPPED, otk_status=KgOtkStatus.PASSED)
        )

    with pytest.raises(PackingKgScrappedError):
        await _pack(session, packing_service, batch.first_dev_eui, packer)


async def test_pack_unit_of_archived_batch_is_rejected(
    session: AsyncSession,
    packing_service: PackingService,
    create_batch: CreateBatch,
    packer: m.User,
) -> None:
    batch = await create_batch(archived=True)
    await _set_otk_status(session, batch.first_dev_eui, KgOtkStatus.PASSED)

    with pytest.raises(PackingBatchArchivedError):
        await _pack(session, packing_service, batch.first_dev_eui, packer)


async def test_pack_unit_with_failed_otk_is_rejected(
    session: AsyncSession,
    packing_service: PackingService,
    create_batch: CreateBatch,
    packer: m.User,
) -> None:
    batch = await create_batch()
    await _set_otk_status(session, batch.first_dev_eui, KgOtkStatus.FAILED)

    with pytest.raises(PackingOtkNotPassedError):
        await _pack(session, packing_service, batch.first_dev_eui, packer)


async def test_pack_unit_under_otk_line_verification_is_rejected(
    session: AsyncSession,
    packing_service: PackingService,
    create_batch: CreateBatch,
    packer: m.User,
) -> None:
    batch = await create_batch()
    await _set_otk_status(session, batch.first_dev_eui, KgOtkStatus.PASSED)
    await _start_session(session, batch, PakDeviceKind.OTK_LINE)

    with pytest.raises(PackingOtkInProgressError):
        await _pack(session, packing_service, batch.first_dev_eui, packer)


async def test_pack_unit_under_engineering_verification_packs_it(
    session: AsyncSession,
    packing_service: PackingService,
    create_batch: CreateBatch,
    packer: m.User,
) -> None:
    batch = await create_batch()
    await _set_otk_status(session, batch.first_dev_eui, KgOtkStatus.PASSED)
    await _start_session(session, batch, PakDeviceKind.ENGINEERING)

    kg = await _pack(session, packing_service, batch.first_dev_eui, packer)

    assert kg.state is KgState.PACKED


async def test_pack_unknown_unit_is_not_found(
    session: AsyncSession,
    packing_service: PackingService,
    packer: m.User,
) -> None:
    with pytest.raises(NotFoundError):
        await _pack(session, packing_service, "ffffffffffffffff", packer)
