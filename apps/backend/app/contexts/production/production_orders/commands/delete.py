from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..exceptions import ProductionOrderCannotBeDeletedError
from ..queries import required_order
from ..repository import ProductionOrderRepository
from ..rules import ensure_management_allowed
from ._common import audit_actor, order_entity


class DeleteProductionOrder:
    def __init__(
        self, repository: ProductionOrderRepository, audit: TransactionalAuditWriter
    ) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(self, *, actor: CurrentPrincipal, order_id: UUID) -> None:
        ensure_management_allowed(actor)
        item = await required_order(self._repository, order_id, for_update=True)
        if await self._repository.has_current_batches(order_id):
            raise ProductionOrderCannotBeDeletedError
        await self._audit.record(
            actor=audit_actor(actor),
            entity=order_entity(item),
            action="production_order.deleted",
            old_data={"name": item.name, "description": item.description},
        )
        await self._repository.delete(item)
