from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.batches import rules as batch_rules
from app.contexts.production.batches.audit import audit_actor, shipment_entity
from app.contexts.production.batches.repository import BatchRepository
from app.contexts.production.exceptions import (
    BatchShipmentKgAlreadyAssignedError,
    BatchShipmentKgStateConflictError,
)
from app.contexts.production.kg.repository import KgRepository
from app.contexts.production.preparation.repository import PreparationRepository
from app.shared.security import CurrentPrincipal

from ..model import BatchShipmentItem
from ..queries import ShipmentQueries
from ..repository import ShipmentRepository
from ..rules import ensure_edit_allowed, ensure_open


class AddShipmentItem:
    def __init__(
        self,
        batches: BatchRepository,
        shipments: ShipmentRepository,
        kg_units: KgRepository,
        preparation: PreparationRepository,
        audit: TransactionalAuditWriter,
        *,
        edit_window: timedelta,
    ) -> None:
        self._queries = ShipmentQueries(batches, shipments)
        self._shipments = shipments
        self._kg_units = kg_units
        self._preparation = preparation
        self._audit = audit
        self._edit_window = edit_window

    async def execute(
        self, *, actor: CurrentPrincipal, batch_id: UUID, shipment_id: UUID, dev_eui: str
    ) -> BatchShipmentItem:
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
        kg = await self._kg_units.get_by_dev_eui(dev_eui, for_update=True)
        if kg is None or kg.batch_id != batch.id:
            raise BatchShipmentKgStateConflictError
        if await self._shipments.find_non_voided_by_kg(kg.dev_eui):
            raise BatchShipmentKgAlreadyAssignedError
        item = await self._shipments.add_item(shipment_id=shipment.id, kg_dev_eui=kg.dev_eui)
        await self._audit.record(
            actor=audit_actor(actor),
            action="batch_shipment.item_added",
            entity=shipment_entity(shipment),
            new_data={"dev_eui": kg.dev_eui},
        )
        return item
