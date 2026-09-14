from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.batches import rules as batch_rules
from app.contexts.production.batches.audit import audit_actor, receipt_entity
from app.contexts.production.batches.compat import LegacyPreparationBridge
from app.contexts.production.batches.repository import BatchRepository
from app.shared.security import CurrentPrincipal

from ..model import BatchReceipt
from ..queries import ReceiptQueries
from ..repository import ReceiptRepository


class CreateReceipt:
    def __init__(
        self,
        batches: BatchRepository,
        receipts: ReceiptRepository,
        preparation: LegacyPreparationBridge,
        audit: TransactionalAuditWriter,
    ) -> None:
        self._queries = ReceiptQueries(batches, receipts)
        self._receipts = receipts
        self._preparation = preparation
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, batch_id: UUID, quantity: int, comment: str | None
    ) -> BatchReceipt:
        batch_rules.ensure_management_allowed(actor)
        batch = await self._queries.required_batch(batch_id, for_update=True)
        job = await self._preparation.get(batch.id, for_update=True)
        batch_rules.ensure_in_production(batch, preparation_status=job.status if job else None)
        receipt = await self._receipts.create(
            batch_id=batch.id, quantity=quantity, comment=comment, created_by_user_id=actor.user_id
        )
        await self._audit.record(
            actor=audit_actor(actor),
            action="batch_receipt.created",
            entity=receipt_entity(receipt),
            new_data={
                "batch_id": str(batch.id),
                "quantity": receipt.quantity,
                "comment": receipt.comment,
            },
        )
        return receipt
