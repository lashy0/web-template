from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.batches import rules as batch_rules
from app.contexts.production.batches.audit import audit_actor, shipment_entity
from app.contexts.production.batches.compat import LegacyPreparationBridge
from app.contexts.production.batches.repository import BatchRepository
from app.shared.security import CurrentPrincipal

from ..model import BatchShipment
from ..queries import ShipmentQueries
from ..repository import ShipmentRepository


class CreateShipment:
    def __init__(
        self,
        batches: BatchRepository,
        shipments: ShipmentRepository,
        preparation: LegacyPreparationBridge,
        audit: TransactionalAuditWriter,
    ) -> None:
        self._queries = ShipmentQueries(batches, shipments)
        self._shipments = shipments
        self._preparation = preparation
        self._audit = audit

    async def execute(
        self, *, actor: CurrentPrincipal, batch_id: UUID, comment: str | None
    ) -> BatchShipment:
        batch_rules.ensure_management_allowed(actor)
        batch = await self._queries.required_batch(batch_id, for_update=True)
        job = await self._preparation.get(batch.id, for_update=True)
        batch_rules.ensure_in_production(batch, preparation_status=job.status if job else None)
        shipment = await self._shipments.create(
            batch_id=batch.id, comment=comment, created_by_user_id=actor.user_id
        )
        await self._audit.record(
            actor=audit_actor(actor),
            action="batch_shipment.created",
            entity=shipment_entity(shipment),
            new_data={"batch_id": str(batch.id), "comment": shipment.comment},
        )
        return shipment
