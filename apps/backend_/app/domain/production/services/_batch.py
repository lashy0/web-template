from __future__ import annotations

from datetime import UTC, datetime, timedelta
from secrets import token_hex
from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import exists, func, insert, literal, select

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
from app.lib.lorawan import derive_dev_eui_range

if TYPE_CHECKING:
    from app.domain.production import schemas as s

BATCH_EDIT_WINDOW = timedelta(minutes=60)
"""How long after creation a batch may still be edited or deleted."""

_RESPONSE_ATTRIBUTES = ("kg_prefix", "kg_version", "production_order", "created_by", "received_qty")


class BatchService(service.SQLAlchemyAsyncRepositoryService[m.Batch]):
    """Application service for production batches and the KG units they allocate."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.Batch]):
        """Batch SQLAlchemy repository."""

        model_type = m.Batch

    repository_type = Repo

    async def create_batch(self, data: s.BatchCreate, *, created_by_id: UUID | None) -> m.Batch:
        """Create the batch and register one KG unit per DevEUI of its range."""
        prefix = await self._lock_prefix(data.kg_prefix_id)

        if data.kg_version_id is not None:
            await self._ensure_current_version(data.kg_version_id)

        if data.production_order_id is not None:
            await self._ensure_assignable_order(data.production_order_id)

        first_serial = prefix.next_serial
        derive_dev_eui_range(prefix.prefix, data.planned_qty, first_serial=first_serial)
        prefix.next_serial = first_serial + data.planned_qty

        batch = await self.create(
            {
                **data.to_dict(),
                "first_serial": first_serial,
                "join_eui": token_hex(8),
                "created_by_id": created_by_id,
            },
            auto_commit=False,
        )
        await self._register_units(batch, prefix)

        return await self._with_relationships(batch)

    async def preview_dev_eui_range(self, prefix_id: UUID, planned_qty: int) -> tuple[str, str]:
        """Return the range the next batch of the prefix would get; nothing is reserved."""
        prefix = await self.repository.session.get(m.KgPrefix, prefix_id)

        if prefix is None:
            raise NotFoundError("DevEUI prefix not found.")

        return derive_dev_eui_range(
            prefix.prefix,
            planned_qty,
            first_serial=prefix.next_serial,
        )

    async def update_batch(self, batch_id: UUID, data: dict[str, object]) -> m.Batch:
        batch = await self._require(batch_id, for_update=True)
        self._ensure_not_archived(batch)
        self._ensure_editable(batch)

        for field, value in data.items():
            setattr(batch, field, value)

        await self.repository.session.flush()

        return batch

    async def assign_production_order(
        self,
        batch_id: UUID,
        production_order_id: UUID | None,
    ) -> m.Batch:
        batch = await self._require(batch_id, for_update=True)
        self._ensure_not_archived(batch)

        if production_order_id == batch.production_order_id:
            return batch

        if production_order_id is not None:
            await self._ensure_assignable_order(production_order_id)

        batch.production_order_id = production_order_id
        await self.repository.session.flush()

        return await self._with_relationships(batch)

    async def complete_batch(self, batch_id: UUID) -> m.Batch:
        batch = await self._require(batch_id, for_update=True)
        self._ensure_not_archived(batch)
        self._ensure_in_production(batch)

        batch.status = BatchStatus.COMPLETED
        batch.completed_at = datetime.now(UTC)
        await self.repository.session.flush()

        return batch

    async def set_archived(self, batch_id: UUID, *, archived: bool) -> m.Batch:
        """Archive or restore a batch; repeating the request keeps the original archive time."""
        batch = await self._require(batch_id, for_update=True)

        if archived and batch.archived_at is None:
            batch.archived_at = datetime.now(UTC)
        elif not archived:
            batch.archived_at = None

        await self.repository.session.flush()

        return batch

    async def delete_batch(self, batch_id: UUID) -> m.Batch:
        """Delete a batch with its KG units; the allocated DevEUIs stay used.

        A batch with receipts, even voided ones, is kept for the record.
        """
        batch = await self._require(batch_id, for_update=True)
        self._ensure_not_archived(batch)
        self._ensure_in_production(batch)
        self._ensure_editable(batch)

        used_units = select(m.KgUnit).where(
            m.KgUnit.batch_id == batch.id,
            m.KgUnit.state != KgState.REGISTERED,
        )
        receipts = select(m.BatchReceipt).where(m.BatchReceipt.batch_id == batch.id)

        if await self.repository.session.scalar(select(exists(used_units) | exists(receipts))):
            raise BatchInUseError

        await self.repository.session.delete(batch)
        await self.repository.session.flush()

        return batch

    async def _register_units(self, batch: m.Batch, prefix: m.KgPrefix) -> None:
        # One statement for the whole range, however large the batch.
        serials = select(
            func.generate_series(
                batch.first_serial,
                batch.first_serial + batch.planned_qty - 1,
            ).label("serial"),
        ).subquery()
        suffix = func.lpad(func.to_hex(serials.c.serial), 6, "0")
        now = func.now()

        await self.repository.session.execute(
            insert(m.KgUnit).from_select(
                ["dev_eui", "short_id", "batch_id", "state", "created_at", "updated_at"],
                select(
                    literal(prefix.prefix) + suffix,
                    literal(f"{prefix.short_code}-") + suffix,
                    literal(batch.id, m.KgUnit.batch_id.type),
                    literal(KgState.REGISTERED, m.KgUnit.state.type),
                    now,
                    now,
                ),
            )
        )

    async def _lock_prefix(self, prefix_id: UUID) -> m.KgPrefix:
        # Serializes allocations from one prefix until the batch commits.
        prefix: m.KgPrefix | None = await self.repository.session.scalar(
            select(m.KgPrefix).where(m.KgPrefix.id == prefix_id).with_for_update()
        )

        if prefix is None:
            raise NotFoundError("DevEUI prefix not found.")

        if prefix.archived_at is not None:
            raise KgPrefixArchivedError(detail="Archived DevEUI prefix cannot allocate DevEUIs.")

        return prefix

    async def _ensure_current_version(self, version_id: UUID) -> None:
        # A shared lock keeps the version from being archived or deleted before the batch commits.
        version: m.KgVersion | None = await self.repository.session.scalar(
            select(m.KgVersion).where(m.KgVersion.id == version_id).with_for_update(read=True)
        )

        if version is None:
            raise NotFoundError("KG version not found.")

        if version.archived_at is not None:
            raise KgVersionArchivedError(detail="Archived KG version cannot be used for a batch.")

    async def _ensure_assignable_order(self, order_id: UUID) -> None:
        # A shared lock keeps the order from being archived or deleted before the batch commits.
        order: m.ProductionOrder | None = await self.repository.session.scalar(
            select(m.ProductionOrder).where(m.ProductionOrder.id == order_id).with_for_update(read=True)
        )

        if order is None:
            raise NotFoundError("Production order not found.")

        if order.archived_at is not None:
            raise ProductionOrderArchivedError(detail="Archived production order cannot receive batches.")

    async def _with_relationships(self, batch: m.Batch) -> m.Batch:
        await self.repository.session.refresh(batch, attribute_names=_RESPONSE_ATTRIBUTES)

        return batch

    async def _require(self, batch_id: UUID, *, for_update: bool = False) -> m.Batch:
        batch = await self.get_one_or_none(
            m.Batch.id == batch_id,
            with_for_update=for_update,
            # A locked read must replace what an earlier read left in the session.
            execution_options={"populate_existing": for_update},
        )

        if batch is None:
            raise NotFoundError("Batch not found.")

        return batch

    @staticmethod
    def _ensure_not_archived(batch: m.Batch) -> None:
        if batch.archived_at is not None:
            raise BatchArchivedError

    @staticmethod
    def _ensure_in_production(batch: m.Batch) -> None:
        if batch.status is BatchStatus.COMPLETED:
            raise BatchCompletedError

    @staticmethod
    def _ensure_editable(batch: m.Batch) -> None:
        if datetime.now(UTC) - batch.created_at > BATCH_EDIT_WINDOW:
            raise BatchEditWindowExpiredError
