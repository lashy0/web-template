from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.batches import rules as batch_rules
from app.contexts.production.batches.audit import audit_actor, receipt_entity
from app.contexts.production.batches.repository import BatchRepository
from app.shared.security import CurrentPrincipal

from ..model import BatchReceipt
from ..queries import ReceiptQueries
from ..repository import ReceiptRepository
from ..rules import ensure_active, ensure_edit_allowed


class VoidReceipt:
    def __init__(
        self,
        batches: BatchRepository,
        receipts: ReceiptRepository,
        audit: TransactionalAuditWriter,
        *,
        edit_window: timedelta,
    ) -> None:
        self._queries = ReceiptQueries(batches, receipts)
        self._receipts = receipts
        self._audit = audit
        self._edit_window = edit_window

    async def execute(
        self, *, actor: CurrentPrincipal, batch_id: UUID, receipt_id: UUID, reason: str
    ) -> BatchReceipt:
        batch_rules.ensure_management_allowed(actor)
        batch = await self._queries.required_batch(batch_id, for_update=True)
        batch_rules.ensure_not_archived(batch)
        receipt = await self._queries.required_receipt(
            receipt_id, batch_id=batch.id, for_update=True
        )
        ensure_active(receipt)
        ensure_edit_allowed(
            receipt, actor=actor, now=datetime.now(UTC), edit_window=self._edit_window
        )
        voided_at = datetime.now(UTC)
        receipt = await self._receipts.void(receipt, voided_at=voided_at, reason=reason)
        await self._audit.record(
            actor=audit_actor(actor),
            action="batch_receipt.voided",
            entity=receipt_entity(receipt),
            old_data={"voided_at": None, "void_reason": None},
            new_data={"voided_at": voided_at.isoformat(), "void_reason": reason},
        )
        return receipt
