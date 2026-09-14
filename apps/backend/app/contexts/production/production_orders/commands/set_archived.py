from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..model import ProductionOrder
from ..queries import required_order
from ..repository import ProductionOrderRepository
from ..rules import ensure_management_allowed
from ._common import audit_actor, order_entity


class SetProductionOrderArchived:
    def __init__(
        self,
        repository: ProductionOrderRepository,
        audit: TransactionalAuditWriter,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._clock = clock

    async def execute(
        self, *, actor: CurrentPrincipal, order_id: UUID, archived: bool
    ) -> ProductionOrder:
        ensure_management_allowed(actor)
        item = await required_order(self._repository, order_id, for_update=True)
        if archived == (item.archived_at is not None):
            return item
        old_archived_at = item.archived_at
        item = await self._repository.set_archived(
            item, archived_at=self._clock() if archived else None
        )
        await self._audit.record(
            actor=audit_actor(actor),
            entity=order_entity(item),
            action="production_order.archived" if archived else "production_order.restored",
            old_data={"archived_at": old_archived_at.isoformat() if old_archived_at else None},
            new_data={"archived_at": item.archived_at.isoformat() if item.archived_at else None},
        )
        return item
