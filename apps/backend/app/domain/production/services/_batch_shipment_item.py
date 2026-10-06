from __future__ import annotations

from typing import TYPE_CHECKING

from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import exists, func, literal, or_, select, text
from sqlalchemy.dialects.postgresql import insert

from app.db import models as m
from app.db.enums import KgState
from app.domain.production.schemas import BatchShipmentUnitRejected, BatchShipmentUnitRejection
from app.domain.production.services._batch_shipment import (
    load_response_attributes,
    lock_batch,
    lock_open_shipment,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from uuid import UUID

    from sqlalchemy import ScalarResult


class BatchShipmentItemService(service.SQLAlchemyAsyncRepositoryService[m.BatchShipmentItem]):
    """The KG units of a batch shipment; they change only while it is open.

    Changes take a shared lock on the batch and lock the shipment first; adding
    by code then locks the units, in the order packing takes them.
    """

    class Repo(repository.SQLAlchemyAsyncRepository[m.BatchShipmentItem]):
        """Batch shipment item SQLAlchemy repository."""

        model_type = m.BatchShipmentItem

    repository_type = Repo

    async def ensure_shipment_exists(self, batch_id: UUID, shipment_id: UUID) -> None:
        shipment = await self.repository.session.get(m.BatchShipment, shipment_id)

        if shipment is None or shipment.batch_id != batch_id:
            raise NotFoundError("Shipment not found.")

    async def add_units(
        self,
        batch_id: UUID,
        shipment_id: UUID,
        codes: Sequence[str],
        *,
        added_by_id: UUID | None,
    ) -> tuple[m.BatchShipment, list[str], list[BatchShipmentUnitRejected]]:
        """Add the units named by DevEUI or short ID; return the shipment, the added DevEUIs and the rejections.

        A code repeated in the request, or naming a unit already named by
        another code, is added once and reported as already added.
        """
        session = self.repository.session
        await lock_batch(session, batch_id)
        shipment = await lock_open_shipment(session, batch_id, shipment_id)
        values = [code.strip().lower() for code in codes]
        units = await self._lock_units(batch_id, values)
        by_value = {value: unit for unit in units for value in (unit.dev_eui, unit.short_id)}
        elsewhere = await self._find_in_other_batches(batch_id, values)
        shipment_of = await self._find_open_items({unit.dev_eui for unit in units})

        added: list[str] = []
        rejected: list[BatchShipmentUnitRejected] = []

        for code, value in zip(codes, values, strict=True):
            unit = by_value.get(value)

            if unit is None:
                reason = (
                    BatchShipmentUnitRejection.OTHER_BATCH
                    if value in elsewhere
                    else BatchShipmentUnitRejection.NOT_FOUND
                )
                rejected.append(BatchShipmentUnitRejected(code=code, reason=reason))
                continue

            rejection = _find_rejection(unit, shipment.id, shipment_of)

            if rejection is not None:
                other_number = (
                    shipment_of[unit.dev_eui][1] if rejection is BatchShipmentUnitRejection.IN_OTHER_SHIPMENT else None
                )
                rejected.append(BatchShipmentUnitRejected(code=code, reason=rejection, shipment_number=other_number))
                continue

            session.add(m.BatchShipmentItem(shipment_id=shipment.id, dev_eui=unit.dev_eui, added_by_id=added_by_id))
            shipment_of[unit.dev_eui] = (shipment.id, shipment.number)
            added.append(unit.dev_eui)

        await session.flush()

        return await load_response_attributes(session, shipment), added, rejected

    async def add_packed_units(
        self,
        batch_id: UUID,
        shipment_id: UUID,
        *,
        added_by_id: UUID | None,
    ) -> m.BatchShipment:
        """Add every packed unit of the batch that is in no other shipment, in one statement."""
        session = self.repository.session
        await lock_batch(session, batch_id)
        shipment = await lock_open_shipment(session, batch_id, shipment_id)
        in_open_shipment = exists().where(
            m.BatchShipmentItem.dev_eui == m.KgUnit.dev_eui,
            m.BatchShipmentItem.voided_at.is_(None),
        )
        now = func.now()

        await session.execute(
            insert(m.BatchShipmentItem)
            .from_select(
                ["shipment_id", "dev_eui", "added_by_id", "created_at", "updated_at"],
                select(
                    literal(shipment.id, m.BatchShipmentItem.shipment_id.type),
                    m.KgUnit.dev_eui,
                    literal(added_by_id, m.BatchShipmentItem.added_by_id.type),
                    now,
                    now,
                ).where(
                    m.KgUnit.batch_id == batch_id,
                    m.KgUnit.state == KgState.PACKED,
                    ~in_open_shipment,
                ),
            )
            # A unit that a concurrent request adds first is skipped, not an error.
            .on_conflict_do_nothing(index_elements=["dev_eui"], index_where=text("voided_at IS NULL"))
        )

        return await load_response_attributes(session, shipment)

    async def remove_unit(self, batch_id: UUID, shipment_id: UUID, dev_eui: str) -> None:
        session = self.repository.session
        await lock_batch(session, batch_id)
        await lock_open_shipment(session, batch_id, shipment_id)
        item = await self.get_one_or_none(
            m.BatchShipmentItem.shipment_id == shipment_id,
            m.BatchShipmentItem.dev_eui == dev_eui,
        )

        if item is None:
            raise NotFoundError("KG unit is not in the shipment.")

        await session.delete(item)
        await session.flush()

    async def _lock_units(self, batch_id: UUID, values: Sequence[str]) -> Sequence[m.KgUnit]:
        units: ScalarResult[m.KgUnit] = await self.repository.session.scalars(
            select(m.KgUnit)
            .where(
                m.KgUnit.batch_id == batch_id,
                or_(m.KgUnit.dev_eui.in_(values), m.KgUnit.short_id.in_(values)),
            )
            .order_by(m.KgUnit.dev_eui)
            .with_for_update(of=m.KgUnit)
            .execution_options(populate_existing=True)
        )

        return units.all()

    async def _find_in_other_batches(self, batch_id: UUID, values: Sequence[str]) -> set[str]:
        """Return the values that name a unit of another batch."""
        rows = await self.repository.session.execute(
            select(m.KgUnit.dev_eui, m.KgUnit.short_id).where(
                m.KgUnit.batch_id != batch_id,
                or_(m.KgUnit.dev_eui.in_(values), m.KgUnit.short_id.in_(values)),
            )
        )

        return {value for row in rows.tuples() for value in row}

    async def _find_open_items(self, dev_euis: set[str]) -> dict[str, tuple[UUID, int]]:
        """Return the shipment that is not voided, its ID and number, of each unit that has one."""
        rows = await self.repository.session.execute(
            select(m.BatchShipmentItem.dev_eui, m.BatchShipment.id, m.BatchShipment.number)
            .join(m.BatchShipment, m.BatchShipment.id == m.BatchShipmentItem.shipment_id)
            .where(
                m.BatchShipmentItem.dev_eui.in_(dev_euis),
                m.BatchShipmentItem.voided_at.is_(None),
            )
        )

        return {dev_eui: (shipment_id, number) for dev_eui, shipment_id, number in rows.tuples()}


def _find_rejection(
    unit: m.KgUnit,
    shipment_id: UUID,
    shipment_of: Mapping[str, tuple[UUID, int]],
) -> BatchShipmentUnitRejection | None:
    held_by = shipment_of.get(unit.dev_eui)

    if held_by is not None:
        return (
            BatchShipmentUnitRejection.ALREADY_ADDED
            if held_by[0] == shipment_id
            else BatchShipmentUnitRejection.IN_OTHER_SHIPMENT
        )

    if unit.state is not KgState.PACKED:
        return BatchShipmentUnitRejection.NOT_PACKED

    return None
