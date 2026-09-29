"""Batch shipment item service integration tests against PostgreSQL."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from advanced_alchemy.exceptions import IntegrityError, NotFoundError
from sqlalchemy import select

from app.db import models as m
from app.domain.production.exceptions import BatchShipmentVoidedError
from app.domain.production.schemas import BatchShipmentUnitRejected, BatchShipmentUnitRejection
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.production.services import BatchShipmentItemService, BatchShipmentService
    from tests.integration.production.conftest import CreateBatch, CreatePrefix, CreateShipment, PackUnits

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


async def _add(
    session: AsyncSession,
    batch_shipment_item_service: BatchShipmentItemService,
    shipment: m.BatchShipment,
    *codes: str,
) -> tuple[m.BatchShipment, Sequence[str], Sequence[BatchShipmentUnitRejected]]:
    async with unit_of_work(session):
        return await batch_shipment_item_service.add_units(shipment.batch_id, shipment.id, codes)


async def test_add_units_accepts_short_id_in_any_case(
    session: AsyncSession,
    batch_shipment_item_service: BatchShipmentItemService,
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch(await create_prefix("a1b2c3d4e5", "ab1"))
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch)

    _, added, _ = await _add(session, batch_shipment_item_service, shipment, " AB1-000001 ")

    assert added == [batch.first_dev_eui]


async def test_add_units_counts_them_in_shipment_quantity(
    session: AsyncSession,
    batch_shipment_item_service: BatchShipmentItemService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui, batch.last_dev_eui)
    shipment = await create_shipment(batch)

    updated, _, _ = await _add(session, batch_shipment_item_service, shipment, batch.first_dev_eui, batch.last_dev_eui)

    assert updated.quantity == 2


async def test_add_unknown_unit_is_rejected_as_not_found(
    session: AsyncSession,
    batch_shipment_item_service: BatchShipmentItemService,
    create_batch: CreateBatch,
    create_shipment: CreateShipment,
) -> None:
    shipment = await create_shipment(await create_batch())

    _, _, rejected = await _add(session, batch_shipment_item_service, shipment, "ffffffffffffffff")

    assert rejected == [
        BatchShipmentUnitRejected(code="ffffffffffffffff", reason=BatchShipmentUnitRejection.NOT_FOUND),
    ]


async def test_add_unit_of_other_batch_is_rejected(
    session: AsyncSession,
    batch_shipment_item_service: BatchShipmentItemService,
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    other = await create_batch(await create_prefix("b1b2c3d4e5", "bb1"))
    await pack_units(other.first_dev_eui)
    shipment = await create_shipment(batch)

    _, _, rejected = await _add(session, batch_shipment_item_service, shipment, other.first_dev_eui)

    assert [item.reason for item in rejected] == [BatchShipmentUnitRejection.OTHER_BATCH]


async def test_add_unit_not_packed_is_rejected(
    session: AsyncSession,
    batch_shipment_item_service: BatchShipmentItemService,
    create_batch: CreateBatch,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    shipment = await create_shipment(batch)

    _, _, rejected = await _add(session, batch_shipment_item_service, shipment, batch.first_dev_eui)

    assert [item.reason for item in rejected] == [BatchShipmentUnitRejection.NOT_PACKED]


async def test_add_unit_in_other_shipment_is_rejected(
    session: AsyncSession,
    batch_shipment_item_service: BatchShipmentItemService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    await create_shipment(batch, batch.first_dev_eui)
    shipment = await create_shipment(batch)

    _, _, rejected = await _add(session, batch_shipment_item_service, shipment, batch.first_dev_eui)

    assert [item.reason for item in rejected] == [BatchShipmentUnitRejection.IN_OTHER_SHIPMENT]


async def test_add_unit_named_twice_is_added_once(
    session: AsyncSession,
    batch_shipment_item_service: BatchShipmentItemService,
    create_prefix: CreatePrefix,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch(await create_prefix("a1b2c3d4e5", "ab1"))
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch)

    _, added, rejected = await _add(session, batch_shipment_item_service, shipment, batch.first_dev_eui, "ab1-000001")

    assert (added, rejected) == (
        [batch.first_dev_eui],
        [BatchShipmentUnitRejected(code="ab1-000001", reason=BatchShipmentUnitRejection.ALREADY_ADDED)],
    )


async def test_add_units_to_voided_shipment_is_rejected(
    session: AsyncSession,
    batch_shipment_service: BatchShipmentService,
    batch_shipment_item_service: BatchShipmentItemService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch)

    async with unit_of_work(session):
        await batch_shipment_service.void_shipment(batch.id, shipment.id, "Cancelled")

    with pytest.raises(BatchShipmentVoidedError):
        await _add(session, batch_shipment_item_service, shipment, batch.first_dev_eui)


async def test_add_packed_units_adds_those_in_no_other_shipment(
    session: AsyncSession,
    batch_shipment_item_service: BatchShipmentItemService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch(planned_qty=4)
    units = (await session.scalars(select(m.KgUnit.dev_eui).order_by(m.KgUnit.dev_eui))).all()
    await pack_units(*units[:3])
    await create_shipment(batch, units[0])
    shipment = await create_shipment(batch)

    async with unit_of_work(session):
        updated = await batch_shipment_item_service.add_packed_units(batch.id, shipment.id)

    assert updated.quantity == 2


async def test_unit_cannot_be_in_two_shipments_that_are_not_voided(
    session: AsyncSession,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    await create_shipment(batch, batch.first_dev_eui)
    other = await create_shipment(batch)

    with pytest.raises(IntegrityError):
        async with unit_of_work(session):
            session.add(m.BatchShipmentItem(shipment_id=other.id, dev_eui=batch.first_dev_eui))


async def test_remove_unit_takes_it_out_of_shipment(
    session: AsyncSession,
    batch_shipment_item_service: BatchShipmentItemService,
    create_batch: CreateBatch,
    pack_units: PackUnits,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    await pack_units(batch.first_dev_eui)
    shipment = await create_shipment(batch, batch.first_dev_eui)

    async with unit_of_work(session):
        await batch_shipment_item_service.remove_unit(batch.id, shipment.id, batch.first_dev_eui)

    assert await session.scalar(select(m.BatchShipmentItem)) is None


async def test_remove_unit_not_in_shipment_is_not_found(
    session: AsyncSession,
    batch_shipment_item_service: BatchShipmentItemService,
    create_batch: CreateBatch,
    create_shipment: CreateShipment,
) -> None:
    batch = await create_batch()
    shipment = await create_shipment(batch)

    with pytest.raises(NotFoundError):
        async with unit_of_work(session):
            await batch_shipment_item_service.remove_unit(batch.id, shipment.id, batch.first_dev_eui)
