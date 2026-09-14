from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..model import ProductionOrder
from ..repository import ProductionOrderRepository
from ..rules import ensure_management_allowed
from ._common import audit_actor, order_entity


class CreateProductionOrder:
    def __init__(
        self, repository: ProductionOrderRepository, audit: TransactionalAuditWriter
    ) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, name: str, description: str | None
    ) -> ProductionOrder:
        ensure_management_allowed(actor)
        item = await self._repository.create(name=name, description=description)
        await self._audit.record(
            actor=audit_actor(actor),
            entity=order_entity(item),
            action="production_order.created",
            new_data={"name": name, "description": description},
        )
        return item
