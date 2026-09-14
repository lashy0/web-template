from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .model import BatchReceipt


class ReceiptRepository:
    """Receipt persistence and reporting projections; never owns a transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, batch_id: UUID, quantity: int, comment: str | None, created_by_user_id: UUID | None
    ) -> BatchReceipt:
        receipt = BatchReceipt(
            batch_id=batch_id,
            quantity=quantity,
            comment=comment,
            created_by_user_id=created_by_user_id,
        )
        self._session.add(receipt)
        await self._session.flush()
        return await self.refresh(receipt)

    async def get(self, receipt_id: UUID, *, for_update: bool = False) -> BatchReceipt | None:
        return await self._session.get(
            BatchReceipt,
            receipt_id,
            with_for_update=for_update,
            populate_existing=for_update,
            options=(selectinload(BatchReceipt.created_by_user),),
        )

    async def get_by_id(self, receipt_id: UUID) -> BatchReceipt | None:
        return await self.get(receipt_id)

    async def refresh(self, receipt: BatchReceipt) -> BatchReceipt:
        await self._session.refresh(receipt)
        await self._session.refresh(receipt, attribute_names=["created_by_user"])
        return receipt

    async def update(self, receipt: BatchReceipt, *, updates: Mapping[str, object]) -> BatchReceipt:
        for field, value in updates.items():
            setattr(receipt, field, value)
        await self._session.flush()
        return await self.refresh(receipt)

    async def update_details(
        self, receipt: BatchReceipt, *, updates: Mapping[str, object]
    ) -> BatchReceipt:
        return await self.update(receipt, updates=updates)

    async def void(
        self, receipt: BatchReceipt, *, voided_at: datetime, reason: str
    ) -> BatchReceipt:
        receipt.voided_at = voided_at
        receipt.void_reason = reason
        await self._session.flush()
        return await self.refresh(receipt)

    async def list_by_batch(
        self, batch_id: UUID, *, include_voided: bool = False
    ) -> list[BatchReceipt]:
        filters: list[ColumnElement[bool]] = [BatchReceipt.batch_id == batch_id]
        if not include_voided:
            filters.append(BatchReceipt.voided_at.is_(None))
        result = await self._session.execute(
            select(BatchReceipt)
            .options(selectinload(BatchReceipt.created_by_user))
            .where(*filters)
            .order_by(BatchReceipt.created_at.desc(), BatchReceipt.id.asc())
        )
        return list(result.scalars())

    async def received_total(self, batch_id: UUID) -> int:
        """Reporting total: only non-voided receipt quantities are received."""
        total = await self._session.scalar(
            select(func.coalesce(func.sum(BatchReceipt.quantity), 0)).where(
                BatchReceipt.batch_id == batch_id, BatchReceipt.voided_at.is_(None)
            )
        )
        return int(total or 0)

    async def get_total(self, batch_id: UUID) -> int:
        return await self.received_total(batch_id)

    async def exists_by_batch(self, batch_id: UUID) -> bool:
        return bool(
            await self._session.scalar(select(exists().where(BatchReceipt.batch_id == batch_id)))
        )
