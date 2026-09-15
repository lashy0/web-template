from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.batches import rules as batch_rules
from app.contexts.production.batches.audit import audit_actor, shipment_entity
from app.contexts.production.batches.repository import BatchRepository
from app.contexts.production.exceptions import BatchShipmentEmptyError
from app.contexts.production.preparation.repository import PreparationRepository
from app.shared.security import CurrentPrincipal

from ..model import BatchShipment
from ..queries import ShipmentQueries
from ..repository import ShipmentRepository
from ..rules import ensure_edit_allowed, ensure_open


class CompleteShipment:
    def __init__(
        self,
        batches: BatchRepository,
        shipments: ShipmentRepository,
        preparation: PreparationRepository,
        audit: TransactionalAuditWriter,
        *,
        edit_window: timedelta,
    ) -> None:
        self._queries = ShipmentQueries(batches, shipments)
        self._shipments = shipments
        self._preparation = preparation
        self._audit = audit
        self._edit_window = edit_window

    async def execute(
        self, *, actor: CurrentPrincipal, batch_id: UUID, shipment_id: UUID
    ) -> BatchShipment:
        batch_rules.ensure_management_allowed(actor)
        batch = await self._queries.required_batch(batch_id, for_update=True)
        job = await self._preparation.get(batch.id, for_update=True)
        batch_rules.ensure_in_production(batch, preparation_status=job.status if job else None)
        shipment = await self._queries.required_shipment(
            shipment_id, batch_id=batch.id, for_update=True
        )
        ensure_open(shipment)
        ensure_edit_allowed(
            shipment, actor=actor, now=datetime.now(UTC), edit_window=self._edit_window
        )
        items = await self._shipments.list_items(shipment.id)
        if not items:
            raise BatchShipmentEmptyError
        completed_at = datetime.now(UTC)
        shipment = await self._shipments.complete(shipment, completed_at=completed_at)
        await self._audit.record(
            actor=audit_actor(actor),
            action="batch_shipment.completed",
            entity=shipment_entity(shipment),
            old_data={"completed_at": None},
            new_data={"completed_at": completed_at.isoformat(), "quantity": len(items)},
        )
        return shipment
