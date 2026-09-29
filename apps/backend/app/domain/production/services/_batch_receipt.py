from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import func, select

from app.db import models as m
from app.db.enums import BatchStatus
from app.domain.production.exceptions import (
    BatchArchivedError,
    BatchCompletedError,
    BatchReceiptEditWindowExpiredError,
    BatchReceiptQuantityExceededError,
    BatchReceiptVoidedError,
)

if TYPE_CHECKING:
    from uuid import UUID

    from app.domain.production import schemas as s

RECEIPT_EDIT_WINDOW = timedelta(minutes=60)
"""How long after creation a receipt may still be edited or voided."""


class BatchReceiptService(service.SQLAlchemyAsyncRepositoryService[m.BatchReceipt]):
    """Application service for the receipts of KG units produced by a batch.

    Every change locks the batch row first, so concurrent receipts of one batch
    see each other's quantities when they check the planned quantity.
    """

    class Repo(repository.SQLAlchemyAsyncRepository[m.BatchReceipt]):
        """Batch receipt SQLAlchemy repository."""

        model_type = m.BatchReceipt

    repository_type = Repo

    async def get_receipt(self, batch_id: UUID, receipt_id: UUID) -> m.BatchReceipt:
        receipt = await self.get_one_or_none(
            m.BatchReceipt.id == receipt_id,
            m.BatchReceipt.batch_id == batch_id,
        )

        if receipt is None:
            raise NotFoundError("Receipt not found.")

        return receipt

    async def ensure_batch_exists(self, batch_id: UUID) -> None:
        if await self.repository.session.get(m.Batch, batch_id) is None:
            raise NotFoundError("Batch not found.")

    async def create_receipt(
        self,
        batch_id: UUID,
        data: s.BatchReceiptCreate,
        *,
        created_by_id: UUID | None,
    ) -> m.BatchReceipt:
        batch = await self._lock_batch(batch_id)

        if batch.status is BatchStatus.COMPLETED:
            raise BatchCompletedError(detail="Completed batch cannot receive KG units.")

        await self._ensure_within_plan(batch, data.quantity)
        receipt = await self.create(
            {
                **data.to_dict(),
                "batch_id": batch.id,
                "created_by_id": created_by_id,
            },
            auto_commit=False,
        )
        await self.repository.session.refresh(receipt, attribute_names=("created_by",))

        return receipt

    async def update_receipt(
        self,
        batch_id: UUID,
        receipt_id: UUID,
        data: dict[str, object],
    ) -> m.BatchReceipt:
        batch = await self._lock_batch(batch_id)
        receipt = await self._lock_editable_receipt(batch, receipt_id)

        quantity = data.get("quantity")

        if isinstance(quantity, int) and quantity > receipt.quantity:
            await self._ensure_within_plan(batch, quantity - receipt.quantity)

        for field, value in data.items():
            setattr(receipt, field, value)

        await self.repository.session.flush()

        return receipt

    async def void_receipt(self, batch_id: UUID, receipt_id: UUID, reason: str) -> m.BatchReceipt:
        batch = await self._lock_batch(batch_id)
        receipt = await self._lock_editable_receipt(batch, receipt_id)

        receipt.voided_at = datetime.now(UTC)
        receipt.void_reason = reason
        await self.repository.session.flush()

        return receipt

    async def _lock_batch(self, batch_id: UUID) -> m.Batch:
        batch: m.Batch | None = await self.repository.session.scalar(
            select(m.Batch)
            .where(m.Batch.id == batch_id)
            .with_for_update(of=m.Batch)
            .execution_options(populate_existing=True)
        )

        if batch is None:
            raise NotFoundError("Batch not found.")

        if batch.archived_at is not None:
            raise BatchArchivedError

        return batch

    async def _lock_editable_receipt(self, batch: m.Batch, receipt_id: UUID) -> m.BatchReceipt:
        receipt: m.BatchReceipt | None = await self.repository.session.scalar(
            select(m.BatchReceipt)
            .where(
                m.BatchReceipt.id == receipt_id,
                m.BatchReceipt.batch_id == batch.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        if receipt is None:
            raise NotFoundError("Receipt not found.")

        if receipt.voided_at is not None:
            raise BatchReceiptVoidedError

        if datetime.now(UTC) - receipt.created_at > RECEIPT_EDIT_WINDOW:
            raise BatchReceiptEditWindowExpiredError

        return receipt

    async def _ensure_within_plan(self, batch: m.Batch, added_qty: int) -> None:
        # Summed here rather than read from ``Batch.received_qty``: the batch
        # row may have been loaded before the lock was taken.
        received: int = (
            await self.repository.session.scalar(
                select(func.coalesce(func.sum(m.BatchReceipt.quantity), 0)).where(
                    m.BatchReceipt.batch_id == batch.id,
                    m.BatchReceipt.voided_at.is_(None),
                )
            )
            or 0
        )
        remaining = batch.planned_qty - received

        if added_qty > remaining:
            raise BatchReceiptQuantityExceededError(
                detail=f"Only {remaining} of {batch.planned_qty} planned KG units remain to be received.",
            )
