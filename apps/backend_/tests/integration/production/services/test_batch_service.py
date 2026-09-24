"""Batch service integration tests against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func, select, update

from app.db import models as m
from app.db.enums import BatchStatus, KgState
from app.domain.production.exceptions import (
    BatchArchivedError,
    BatchCompletedError,
    BatchEditWindowExpiredError,
    BatchInUseError,
    KgPrefixArchivedError,
    KgVersionArchivedError,
    ProductionOrderArchivedError,
)
from app.domain.production.schemas import BatchCreate
from app.lib.lorawan import DEV_EUI_SERIAL_MAX, ActivationType, DevEuiRangeOverflowError, LoRaWanVersion
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.production.services import BatchService
    from tests.integration.production.conftest import CreateBatch, CreateOrder, CreatePrefix, CreateVersion

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


def _batch_data(
    prefix_id: UUID,
    *,
    planned_qty: int = 3,
    kg_version_id: UUID | None = None,
    production_order_id: UUID | None = None,
) -> BatchCreate:
    return BatchCreate(
        name="Batch",
        kg_prefix_id=prefix_id,
        planned_qty=planned_qty,
        day_plan_qty=planned_qty,
        activation_type=ActivationType.OTAA,
        lorawan_version=LoRaWanVersion.V1_0,
        kg_version_id=kg_version_id,
        production_order_id=production_order_id,
    )


async def _age(session: AsyncSession, batch: m.Batch, *, hours: int) -> None:
    async with unit_of_work(session):
        await session.execute(
            update(m.Batch).where(m.Batch.id == batch.id).values(created_at=datetime.now(UTC) - timedelta(hours=hours))
        )


async def _unit_count(session: AsyncSession, batch_id: UUID) -> int:
    return await session.scalar(select(func.count()).where(m.KgUnit.batch_id == batch_id)) or 0


async def test_first_batch_starts_at_first_serial(create_prefix: CreatePrefix, create_batch: CreateBatch) -> None:
    prefix = await create_prefix("a1b2c3d4e5")

    batch = await create_batch(prefix, planned_qty=3)

    assert (batch.first_dev_eui, batch.last_dev_eui) == ("a1b2c3d4e5000001", "a1b2c3d4e5000003")


async def test_next_batch_continues_after_previous_range(
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
) -> None:
    prefix = await create_prefix("a1b2c3d4e5")
    await create_batch(prefix, planned_qty=3)

    batch = await create_batch(prefix, planned_qty=2)

    assert (batch.first_dev_eui, batch.last_dev_eui) == ("a1b2c3d4e5000004", "a1b2c3d4e5000005")


async def test_create_batch_registers_one_unit_per_dev_eui(
    session: AsyncSession,
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
) -> None:
    prefix = await create_prefix("a1b2c3d4e5", "ab1")

    batch = await create_batch(prefix, planned_qty=3)

    units = (await session.scalars(select(m.KgUnit).where(m.KgUnit.batch_id == batch.id))).all()
    assert sorted((unit.dev_eui, unit.short_id, unit.state) for unit in units) == [
        ("a1b2c3d4e5000001", "ab1-000001", KgState.REGISTERED),
        ("a1b2c3d4e5000002", "ab1-000002", KgState.REGISTERED),
        ("a1b2c3d4e5000003", "ab1-000003", KgState.REGISTERED),
    ]


async def test_deleted_batch_dev_euis_are_not_reissued(
    session: AsyncSession,
    batch_service: BatchService,
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
) -> None:
    prefix = await create_prefix("a1b2c3d4e5")
    deleted = await create_batch(prefix, planned_qty=3)

    async with unit_of_work(session):
        await batch_service.delete_batch(deleted.id)

    batch = await create_batch(prefix, planned_qty=1)

    assert batch.first_dev_eui == "a1b2c3d4e5000004"


async def test_create_batch_beyond_prefix_capacity_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    create_prefix: CreatePrefix,
) -> None:
    prefix = await create_prefix()

    async with unit_of_work(session):
        await session.execute(
            update(m.KgPrefix).where(m.KgPrefix.id == prefix.id).values(next_serial=DEV_EUI_SERIAL_MAX)
        )

    with pytest.raises(DevEuiRangeOverflowError):
        async with unit_of_work(session):
            await batch_service.create_batch(_batch_data(prefix.id, planned_qty=2), created_by_id=None)


async def test_create_batch_from_archived_prefix_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    create_prefix: CreatePrefix,
) -> None:
    prefix = await create_prefix(archived=True)

    with pytest.raises(KgPrefixArchivedError):
        async with unit_of_work(session):
            await batch_service.create_batch(_batch_data(prefix.id), created_by_id=None)


async def test_create_batch_with_archived_version_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    create_prefix: CreatePrefix,
    create_version: CreateVersion,
) -> None:
    prefix = await create_prefix()
    version = await create_version(archived=True)

    with pytest.raises(KgVersionArchivedError):
        async with unit_of_work(session):
            await batch_service.create_batch(_batch_data(prefix.id, kg_version_id=version.id), created_by_id=None)


async def test_create_batch_for_archived_order_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    create_prefix: CreatePrefix,
    create_order: CreateOrder,
) -> None:
    prefix = await create_prefix()
    order = await create_order(archived=True)

    with pytest.raises(ProductionOrderArchivedError):
        async with unit_of_work(session):
            await batch_service.create_batch(
                _batch_data(prefix.id, production_order_id=order.id),
                created_by_id=None,
            )


async def test_update_batch_after_edit_window_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()
    await _age(session, batch, hours=2)

    with pytest.raises(BatchEditWindowExpiredError):
        async with unit_of_work(session):
            await batch_service.update_batch(batch.id, {"name": "Renamed"})


async def test_update_archived_batch_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch(archived=True)

    with pytest.raises(BatchArchivedError):
        async with unit_of_work(session):
            await batch_service.update_batch(batch.id, {"name": "Renamed"})


async def test_assign_archived_order_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    create_batch: CreateBatch,
    create_order: CreateOrder,
) -> None:
    batch = await create_batch()
    order = await create_order(archived=True)

    with pytest.raises(ProductionOrderArchivedError):
        async with unit_of_work(session):
            await batch_service.assign_production_order(batch.id, order.id)


async def test_complete_batch_records_completion(
    session: AsyncSession,
    batch_service: BatchService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    async with unit_of_work(session):
        await batch_service.complete_batch(batch.id)

    stored = await batch_service.get(batch.id)
    assert (stored.status, stored.completed_at is not None) == (BatchStatus.COMPLETED, True)


async def test_complete_completed_batch_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    async with unit_of_work(session):
        await batch_service.complete_batch(batch.id)

    with pytest.raises(BatchCompletedError):
        async with unit_of_work(session):
            await batch_service.complete_batch(batch.id)


async def test_archive_batch_again_keeps_original_archive_time(
    session: AsyncSession,
    batch_service: BatchService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch(archived=True)
    archived_at = batch.archived_at

    async with unit_of_work(session):
        await batch_service.set_archived(batch.id, archived=True)

    assert (await batch_service.get(batch.id)).archived_at == archived_at


async def test_delete_batch_removes_its_units(
    session: AsyncSession,
    batch_service: BatchService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    async with unit_of_work(session):
        await batch_service.delete_batch(batch.id)

    assert await _unit_count(session, batch.id) == 0


async def test_delete_batch_with_scrapped_unit_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    async with unit_of_work(session):
        await session.execute(
            update(m.KgUnit).where(m.KgUnit.dev_eui == batch.first_dev_eui).values(state=KgState.SCRAPPED)
        )

    with pytest.raises(BatchInUseError):
        async with unit_of_work(session):
            await batch_service.delete_batch(batch.id)


async def test_delete_completed_batch_is_rejected(
    session: AsyncSession,
    batch_service: BatchService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    async with unit_of_work(session):
        await batch_service.complete_batch(batch.id)

    with pytest.raises(BatchCompletedError):
        async with unit_of_work(session):
            await batch_service.delete_batch(batch.id)
