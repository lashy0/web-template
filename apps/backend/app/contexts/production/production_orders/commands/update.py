from collections.abc import Mapping
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..model import ProductionOrder
from ..queries import required_order
from ..repository import ProductionOrderRepository
from ..rules import ensure_management_allowed
from ._common import audit_actor, order_entity


class UpdateProductionOrder:
    def __init__(
        self, repository: ProductionOrderRepository, audit: TransactionalAuditWriter
    ) -> None:
        self._repository = repository
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, order_id: UUID, updates: Mapping[str, object]
    ) -> ProductionOrder:
        ensure_management_allowed(actor)
        item = await required_order(self._repository, order_id, for_update=True)
        changed = {
            key: value
            for key, value in updates.items()
            if key in ("name", "description") and getattr(item, key) != value
        }
        if not changed:
            return item
        old_data = {key: getattr(item, key) for key in changed}
        item = await self._repository.update_details(item, updates=changed)
        await self._audit.record(
            actor=audit_actor(actor),
            entity=order_entity(item),
            action="production_order.updated",
            old_data=old_data,
            new_data=dict(changed),
        )
        return item
