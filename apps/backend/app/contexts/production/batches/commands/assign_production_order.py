from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..audit import audit_actor, batch_entity
from ..compat import LegacyProductionOrderBridge
from ..model import Batch
from ..queries import required_batch
from ..repository import BatchRepository
from ..rules import ensure_management_allowed, ensure_not_archived


class AssignProductionOrder:
    def __init__(
        self,
        repository: BatchRepository,
        orders: LegacyProductionOrderBridge,
        audit: TransactionalAuditWriter,
    ) -> None:
        self._repository = repository
        self._orders = orders
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, batch_id: UUID, production_order_id: UUID | None
    ) -> Batch:
        ensure_management_allowed(actor)
        batch = await required_batch(self._repository, batch_id, for_update=True)
        ensure_not_archived(batch)
        old_id = batch.production_order_id
        if old_id == production_order_id:
            return batch
        if production_order_id is not None:
            await self._orders.ensure_assignable(production_order_id)
        batch = await self._repository.update(
            batch, updates={"production_order_id": production_order_id}
        )
        await self._audit.record(
            actor=audit_actor(actor),
            action="batch.production_order_changed",
            entity=batch_entity(batch),
            old_data={"production_order_id": str(old_id) if old_id else None},
            new_data={
                "production_order_id": str(production_order_id) if production_order_id else None
            },
        )
        return batch
