from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.batches import rules as batch_rules
from app.contexts.production.batches.audit import audit_actor, shipment_entity
from app.contexts.production.batches.repository import BatchRepository
from app.contexts.production.exceptions import BatchShipmentItemNotFoundError
from app.shared.security import CurrentPrincipal

from ..queries import ShipmentQueries
from ..repository import ShipmentRepository
from ..rules import ensure_edit_allowed, ensure_open


class RemoveShipmentItem:
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
        self, *, actor: CurrentPrincipal, batch_id: UUID, shipment_id: UUID, dev_eui: str
    ) -> None:
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
        item = await self._shipments.get_item(shipment_id=shipment.id, kg_dev_eui=dev_eui)
        if item is None:
            raise BatchShipmentItemNotFoundError
        await self._shipments.delete_item(item)
        await self._audit.record(
            actor=audit_actor(actor),
            action="batch_shipment.item_removed",
            entity=shipment_entity(shipment),
            old_data={"dev_eui": dev_eui},
        )
