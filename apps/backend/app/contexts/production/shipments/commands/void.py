from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.batches import rules as batch_rules
from app.contexts.production.batches.audit import audit_actor, shipment_entity
from app.contexts.production.batches.repository import BatchRepository
from app.shared.security import CurrentPrincipal

from ..model import BatchShipment
from ..queries import ShipmentQueries
from ..repository import ShipmentRepository
from ..rules import ensure_edit_allowed, ensure_not_voided


class VoidShipment:
    """Void a shipment without recreating a retired physical KG shipment state.

    The KG schema's current physical state has no PACKED/SHIPPED values. The
    preceding KG state split deliberately made shipment membership/reporting the
    authoritative source, so no unconditional KG update is performed here.
    """

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
        self, *, actor: CurrentPrincipal, batch_id: UUID, shipment_id: UUID, reason: str
    ) -> BatchShipment:
        batch_rules.ensure_management_allowed(actor)
        batch = await self._queries.required_batch(batch_id, for_update=True)
        batch_rules.ensure_not_archived(batch)
        shipment = await self._queries.required_shipment(
            shipment_id, batch_id=batch.id, for_update=True
        )
        ensure_not_voided(shipment)
        ensure_edit_allowed(
            shipment, actor=actor, now=datetime.now(UTC), edit_window=self._edit_window
        )
        items = await self._shipments.list_items(shipment.id)
        voided_at = datetime.now(UTC)
        shipment = await self._shipments.void(shipment, voided_at=voided_at, reason=reason)
        await self._audit.record(
            actor=audit_actor(actor),
            action="batch_shipment.voided",
            entity=shipment_entity(shipment),
            old_data={"voided_at": None, "void_reason": None},
            new_data={
                "voided_at": voided_at.isoformat(),
                "void_reason": reason,
                "quantity": len(items),
            },
        )
        return shipment
