from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.extensions.litestar import repository, service
from advanced_alchemy.service import schema_dump
from sqlalchemy import func, select, update

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
from app.lib.concurrency import ensure_unchanged

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.production import schemas as s

SHIPMENT_VOID_WINDOW = timedelta(minutes=60)
"""How long after completion a shipment may still be voided."""

_RESPONSE_ATTRIBUTES = ("created_by", "completed_by", "voided_by", "quantity")


class BatchShipmentService(service.SQLAlchemyAsyncRepositoryService[m.BatchShipment]):
    """Application service for the shipments of packed KG units of a batch.

    Every change takes a shared lock on the batch, so it cannot be archived
    meanwhile, and then locks the shipment, so its units and status change one
    request at a time.
    """

    class Repo(repository.SQLAlchemyAsyncRepository[m.BatchShipment]):
        """Batch shipment SQLAlchemy repository."""

        model_type = m.BatchShipment

    repository_type = Repo

    async def get_shipment(self, batch_id: UUID, shipment_id: UUID) -> m.BatchShipment:
        shipment = await self.get_one_or_none(
            m.BatchShipment.id == shipment_id,
            m.BatchShipment.batch_id == batch_id,
        )

        if shipment is None:
            raise NotFoundError("Shipment not found.")

        return shipment

    async def ensure_batch_exists(self, batch_id: UUID) -> None:
        if await self.repository.session.get(m.Batch, batch_id) is None:
            raise NotFoundError("Batch not found.")

    async def create_shipment(
        self,
        batch_id: UUID,
        data: s.BatchShipmentCreate,
        *,
        created_by_id: UUID | None,
    ) -> m.BatchShipment:
        batch = await lock_batch(self.repository.session, batch_id)
        shipment = await self.create(
            {**schema_dump(data), "batch_id": batch.id, "created_by_id": created_by_id},
            auto_commit=False,
        )

        return await load_response_attributes(self.repository.session, shipment)

    async def update_shipment(
        self,
        batch_id: UUID,
        shipment_id: UUID,
        data: dict[str, object],
        *,
        expected_updated_at: datetime | None = None,
    ) -> m.BatchShipment:
        session = self.repository.session
        await lock_batch(session, batch_id)
        shipment = await lock_open_shipment(session, batch_id, shipment_id)
        ensure_unchanged(shipment, expected_updated_at)

        for field, value in data.items():
            setattr(shipment, field, value)

        await session.flush()

        return await load_response_attributes(session, shipment)

    async def complete_shipment(
        self,
        batch_id: UUID,
        shipment_id: UUID,
        *,
        completed_by_id: UUID | None,
        expected_quantity: int | None = None,
    ) -> m.BatchShipment:
        """Ship the units: each goes from ``packed`` to ``shipped``.

        ``expected_quantity`` is the count the user saw; another count means
        someone changed the units meanwhile, and nothing is shipped. ``None``
        skips the check.
        """
        session = self.repository.session
        await lock_batch(session, batch_id)
        shipment = await lock_open_shipment(session, batch_id, shipment_id)
        quantity = await _count_items(session, shipment.id)

        if quantity == 0:
            raise BatchShipmentEmptyError

        if expected_quantity is not None and quantity != expected_quantity:
            raise BatchShipmentQuantityChangedError

        if await _move_units(session, shipment.id, KgState.PACKED, KgState.SHIPPED) != quantity:
            raise BatchShipmentKgNotPackedError

        shipment.status = BatchShipmentStatus.COMPLETED
        shipment.completed_at = datetime.now(UTC)
        shipment.completed_by_id = completed_by_id
        await session.flush()

        return await load_response_attributes(session, shipment)

    async def void_shipment(
        self,
        batch_id: UUID,
        shipment_id: UUID,
        reason: str,
        *,
        voided_by_id: UUID | None,
    ) -> m.BatchShipment:
        """Void the shipment and release its units; shipped units return to ``packed``."""
        session = self.repository.session
        await lock_batch(session, batch_id)
        shipment = await lock_shipment(session, batch_id, shipment_id)
        now = datetime.now(UTC)

        if shipment.status is BatchShipmentStatus.VOIDED:
            raise BatchShipmentVoidedError

        if shipment.completed_at is not None:
            if now - shipment.completed_at > SHIPMENT_VOID_WINDOW:
                raise BatchShipmentVoidWindowExpiredError

            await _move_units(session, shipment.id, KgState.SHIPPED, KgState.PACKED)

        await session.execute(
            update(m.BatchShipmentItem)
            .where(m.BatchShipmentItem.shipment_id == shipment.id)
            .values(voided_at=now)
            .execution_options(synchronize_session=False)
        )
        shipment.status = BatchShipmentStatus.VOIDED
        shipment.voided_at = now
        shipment.voided_by_id = voided_by_id
        shipment.void_reason = reason
        await session.flush()

        return await load_response_attributes(session, shipment)


async def lock_batch(session: AsyncSession, batch_id: UUID) -> m.Batch:
    """Take a shared lock on the batch, which must not be archived; a completed batch may ship."""
    batch: m.Batch | None = await session.scalar(
        select(m.Batch)
        .where(m.Batch.id == batch_id)
        .with_for_update(read=True, of=m.Batch)
        .execution_options(populate_existing=True)
    )

    if batch is None:
        raise NotFoundError("Batch not found.")

    if batch.archived_at is not None:
        raise BatchArchivedError

    return batch


async def lock_shipment(
    session: AsyncSession,
    batch_id: UUID,
    shipment_id: UUID,
) -> m.BatchShipment:
    shipment: m.BatchShipment | None = await session.scalar(
        select(m.BatchShipment)
        .where(
            m.BatchShipment.id == shipment_id,
            m.BatchShipment.batch_id == batch_id,
        )
        .with_for_update(of=m.BatchShipment)
        # A locked read must replace what an earlier read left in the session.
        .execution_options(populate_existing=True)
    )

    if shipment is None:
        raise NotFoundError("Shipment not found.")

    return shipment


async def lock_open_shipment(
    session: AsyncSession,
    batch_id: UUID,
    shipment_id: UUID,
) -> m.BatchShipment:
    shipment = await lock_shipment(session, batch_id, shipment_id)

    if shipment.status is BatchShipmentStatus.COMPLETED:
        raise BatchShipmentCompletedError

    if shipment.status is BatchShipmentStatus.VOIDED:
        raise BatchShipmentVoidedError

    return shipment


async def load_response_attributes(
    session: AsyncSession,
    shipment: m.BatchShipment,
) -> m.BatchShipment:
    """Reload what the response shows; ``quantity`` is not refreshed by a flush."""
    await session.refresh(shipment, attribute_names=_RESPONSE_ATTRIBUTES)

    return shipment


async def _count_items(session: AsyncSession, shipment_id: UUID) -> int:
    return (
        await session.scalar(
            select(func.count()).select_from(m.BatchShipmentItem).where(m.BatchShipmentItem.shipment_id == shipment_id)
        )
        or 0
    )


async def _move_units(
    session: AsyncSession,
    shipment_id: UUID,
    source: KgState,
    target: KgState,
) -> int:
    """Move the units of the shipment in ``source`` to ``target``; return how many moved."""
    result = await session.execute(
        update(m.KgUnit)
        .where(
            m.KgUnit.dev_eui.in_(
                select(m.BatchShipmentItem.dev_eui).where(m.BatchShipmentItem.shipment_id == shipment_id)
            ),
            m.KgUnit.state == source,
        )
        .values(state=target)
        .execution_options(synchronize_session=False)
    )

    return result.rowcount  # type: ignore[attr-defined, no-any-return]
