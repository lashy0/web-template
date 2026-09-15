from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.domains.production.batches import rules as batch_rules
from app.domains.production.batches.audit import audit_actor, receipt_entity
from app.domains.production.batches.repository import BatchRepository
from app.shared.security import CurrentPrincipal

from ..model import BatchReceipt
from ..queries import ReceiptQueries
from ..repository import ReceiptRepository
from ..rules import ensure_active, ensure_edit_allowed


class UpdateReceipt:
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
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        receipt_id: UUID,
        updates: Mapping[str, object],
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
        if not updates:
            return receipt
        old_values = {field: getattr(receipt, field) for field in updates}
        receipt = await self._receipts.update(receipt, updates=updates)
        changed = {
            field: value
            for field, value in ((field, getattr(receipt, field)) for field in updates)
            if value != old_values[field]
        }
        if changed:
            await self._audit.record(
                actor=audit_actor(actor),
                action="batch_receipt.updated",
                entity=receipt_entity(receipt),
                old_data={field: old_values[field] for field in changed},
                new_data=changed,
            )
        return receipt
