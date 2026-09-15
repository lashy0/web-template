from __future__ import annotations

from uuid import UUID

from app.contexts.production.batches.model import Batch
from app.contexts.production.batches.repository import BatchRepository
from app.contexts.production.exceptions import BatchNotFoundError, BatchReceiptNotFoundError

from .model import BatchReceipt
from .repository import ReceiptRepository


class ReceiptQueries:
    def __init__(self, batches: BatchRepository, receipts: ReceiptRepository) -> None:
        self._batches = batches
        self._receipts = receipts

    async def list(self, batch_id: UUID, *, include_voided: bool = False) -> list[BatchReceipt]:
        await self.required_batch(batch_id)
        return await self._receipts.list_by_batch(batch_id, include_voided=include_voided)

    async def received_total(self, batch_id: UUID) -> int:
        await self.required_batch(batch_id)
        return await self._receipts.received_total(batch_id)

    async def required_batch(self, batch_id: UUID, *, for_update: bool = False) -> Batch:
        batch = await self._batches.get(batch_id, for_update=for_update)
        if batch is None:
            raise BatchNotFoundError
        return batch

    async def required_receipt(
        self, receipt_id: UUID, *, batch_id: UUID, for_update: bool = False
    ) -> BatchReceipt:
        receipt = await self._receipts.get(receipt_id, for_update=for_update)
        if receipt is None or receipt.batch_id != batch_id:
            raise BatchReceiptNotFoundError
        return receipt
