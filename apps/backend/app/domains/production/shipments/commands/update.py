from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.domains.production.batches import rules as batch_rules
from app.domains.production.batches.audit import audit_actor, shipment_entity
from app.domains.production.batches.repository import BatchRepository
from app.shared.security import CurrentPrincipal

from ..model import BatchShipment
from ..queries import ShipmentQueries
from ..repository import ShipmentRepository
from ..rules import ensure_edit_allowed, ensure_open


class UpdateShipment:
    def __init__(
        self,
        batches: BatchRepository,
        shipments: ShipmentRepository,
        audit: TransactionalAuditWriter,
        *,
        edit_window: timedelta,
    ) -> None:
        self._queries = ShipmentQueries(batches, shipments)
        self._shipments = shipments
        self._audit = audit
        self._edit_window = edit_window

    async def execute(
        self,
        *,
        actor: CurrentPrincipal,
        batch_id: UUID,
        shipment_id: UUID,
        updates: Mapping[str, object],
    ) -> BatchShipment:
        batch_rules.ensure_management_allowed(actor)
        batch = await self._queries.required_batch(batch_id, for_update=True)
        batch_rules.ensure_not_archived(batch)
        shipment = await self._queries.required_shipment(
            shipment_id, batch_id=batch.id, for_update=True
        )
        ensure_open(shipment)
        ensure_edit_allowed(
            shipment, actor=actor, now=datetime.now(UTC), edit_window=self._edit_window
        )
        if not updates:
            return shipment
        old_values = {field: getattr(shipment, field) for field in updates}
        shipment = await self._shipments.update(shipment, updates=updates)
        changed = {
            field: value
            for field, value in ((field, getattr(shipment, field)) for field in updates)
            if value != old_values[field]
        }
        if changed:
            await self._audit.record(
                actor=audit_actor(actor),
                action="batch_shipment.updated",
                entity=shipment_entity(shipment),
                old_data={field: old_values[field] for field in changed},
                new_data=changed,
            )
        return shipment
