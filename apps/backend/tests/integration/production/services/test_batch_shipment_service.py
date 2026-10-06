"""Batch shipment service integration tests against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from advanced_alchemy.exceptions import NotFoundError
from sqlalchemy import select, update

from app.db import models as m
from app.db.enums import BatchShipmentStatus, KgState
from app.domain.production.exceptions import (
    BatchArchivedError,
    BatchShipmentCompletedError,
    BatchShipmentEmptyError,
    BatchShipmentKgNotPackedError,
    BatchShipmentQuantityChangedError,
    BatchShipmentVoidedError,
    BatchShipmentVoidWindowExpiredError,
)
from app.domain.production.schemas import BatchShipmentCreate
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.production.services import BatchService, BatchShipmentItemService, BatchShipmentService
    from tests.integration.production.conftest import CreateBatch, CreatePrefix, CreateShipment, PackUnits

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


async def _states(session: AsyncSession, *dev_euis: str) -> list[KgState]:
    session.expunge_all()
    units = await session.scalars(select(m.KgUnit).where(m.KgUnit.dev_eui.in_(dev_euis)).order_by(m.KgUnit.dev_eui))

    return [unit.state for unit in units]


async def _complete(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    shipment: m.BatchShipment,
    expected_quantity: int | None = None,
) -> m.BatchShipment:
    async with unit_of_work(session):
        return await batch_shipment_service.complete_shipment(
            shipment.batch_id, shipment.id, expected_quantity=expected_quantity, completed_by_id=None
        )


async def _void(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    shipment: m.BatchShipment,
) -> m.BatchShipment:
    async with unit_of_work(session):
        return await batch_shipment_service.void_shipment(
            shipment.batch_id, shipment.id, "Pickup postponed", voided_by_id=None
        )


async def test_create_shipment_numbers_shipments_in_sequence(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    async with unit_of_work(session):
        first = await batch_shipment_service.create_shipment(batch.id, BatchShipmentCreate(), created_by_id=None)
        second = await batch_shipment_service.create_shipment(batch.id, BatchShipmentCreate(), created_by_id=None)

    assert (second.number - first.number, first.status, first.quantity) == (1, BatchShipmentStatus.OPEN, 0)


async def test_create_shipment_of_completed_batch_opens_it(
    session: AsyncSession,
    batch_service: BatchService,
    batch_shipment_service: BatchShipmentService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch()

    async with unit_of_work(session):
        await batch_service.complete_batch(batch.id)
        shipment = await batch_shipment_service.create_shipment(batch.id, BatchShipmentCreate(), created_by_id=None)

    assert shipment.status is BatchShipmentStatus.OPEN


async def test_create_shipment_of_archived_batch_is_rejected(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    create_batch: CreateBatch,
) -> None:
    batch = await create_batch(archived=True)

    with pytest.raises(BatchArchivedError):
        async with unit_of_work(session):
            await batch_shipment_service.create_shipment(batch.id, BatchShipmentCreate(), created_by_id=None)


async def test_create_shipment_of_unknown_batch_is_not_found(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
) -> None:
    with pytest.raises(NotFoundError):
        async with unit_of_work(session):
            await batch_shipment_service.create_shipment(uuid4(), BatchShipmentCreate(), created_by_id=None)


async def test_update_shipment_changes_open_shipment(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    create_batch: CreateBatch,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    shipment = await create_shipment(batch)

    async with unit_of_work(session):
        updated = await batch_shipment_service.update_shipment(batch.id, shipment.id, {"comment": "Thursday"})

    assert updated.comment == "Thursday"


async def test_update_shipment_of_other_batch_is_not_found(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    other = await create_batch(await create_prefix("b1b2c3d4e5", "bb1"))
    shipment = await create_shipment(batch)

    with pytest.raises(NotFoundError):
        async with unit_of_work(session):
            await batch_shipment_service.update_shipment(other.id, shipment.id, {"comment": "Thursday"})


async def test_update_completed_shipment_is_rejected(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui, completed=True)

    with pytest.raises(BatchShipmentCompletedError):
        async with unit_of_work(session):
            await batch_shipment_service.update_shipment(batch.id, shipment.id, {"comment": "Late"})


async def test_complete_shipment_marks_its_units_shipped(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui, batch.last_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui, batch.last_dev_eui)

    await _complete(session, batch_shipment_service, shipment)

    assert await _states(session, batch.first_dev_eui, batch.last_dev_eui) == [KgState.SHIPPED, KgState.SHIPPED]


async def test_complete_shipment_counts_units_as_shipped_and_still_packed(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    batch_service: BatchService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui, batch.last_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui)
    await _complete(session, batch_shipment_service, shipment)
    session.expunge_all()

    reloaded = await batch_service.get(batch.id)

    assert (reloaded.packed_qty, reloaded.shipped_qty) == (2, 1)


async def test_complete_shipment_whose_units_changed_is_rejected(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui, batch.last_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui, batch.last_dev_eui)

    with pytest.raises(BatchShipmentQuantityChangedError):
        await _complete(session, batch_shipment_service, shipment, expected_quantity=1)


async def test_complete_empty_shipment_is_rejected(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    create_batch: CreateBatch,
    create_shipment: CreateShipment,
) -> None:
    shipment = await create_shipment(await create_batch())

    with pytest.raises(BatchShipmentEmptyError):
        await _complete(session, batch_shipment_service, shipment)


async def test_complete_shipment_with_unit_no_longer_packed_is_rejected(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui)

    async with unit_of_work(session):
        await session.execute(
            update(m.KgUnit)
            .where(m.KgUnit.dev_eui == batch.first_dev_eui)
            .values(state=KgState.SCRAPPED, packed_at=None)
        )

    with pytest.raises(BatchShipmentKgNotPackedError):
        await _complete(session, batch_shipment_service, shipment)


async def test_void_open_shipment_releases_its_units(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    batch_shipment_item_service: BatchShipmentItemService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    voided = await create_shipment(batch, batch.first_dev_eui)
    await _void(session, batch_shipment_service, voided)
    other = await create_shipment(batch)

    async with unit_of_work(session):
        _, added, _ = await batch_shipment_item_service.add_units(
            batch.id,
            other.id,
            [batch.first_dev_eui],
            added_by_id=None,
        )

    assert added == [batch.first_dev_eui]


async def test_void_completed_shipment_returns_units_to_packed(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui, completed=True)

    await _void(session, batch_shipment_service, shipment)

    assert await _states(session, batch.first_dev_eui) == [KgState.PACKED]


async def test_void_shipment_completed_long_ago_is_rejected(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui, completed=True)

    async with unit_of_work(session):
        await session.execute(
            update(m.BatchShipment)
            .where(m.BatchShipment.id == shipment.id)
            .values(completed_at=datetime.now(UTC) - timedelta(minutes=61))
        )

    with pytest.raises(BatchShipmentVoidWindowExpiredError):
        await _void(session, batch_shipment_service, shipment)


async def test_void_voided_shipment_is_rejected(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    create_batch: CreateBatch,
    create_shipment: CreateShipment,
) -> None:
    shipment = await create_shipment(await create_batch())
    await _void(session, batch_shipment_service, shipment)

    with pytest.raises(BatchShipmentVoidedError):
        await _void(session, batch_shipment_service, shipment)
