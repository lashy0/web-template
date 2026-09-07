from __future__ import annotations

from app.auth.principal import CurrentPrincipal
from app.modules.audit.types import AuditActor, AuditEntity

from ..models import Batch, BatchReceipt, BatchShipment


def audit_actor(actor: CurrentPrincipal) -> AuditActor:
    return AuditActor.user(
        actor.user_id,
        name=actor.name,
        login=actor.login,
    )


def batch_entity(batch: Batch) -> AuditEntity:
    return AuditEntity(
        type="batch",
        id=str(batch.id),
        display_name=batch.name,
        identifier=str(batch.id),
    )


def receipt_entity(receipt: BatchReceipt) -> AuditEntity:
    return AuditEntity(
        type="batch_receipt",
        id=str(receipt.id),
        display_name=f"Receipt {receipt.id}",
        identifier=str(receipt.batch_id),
    )


def shipment_entity(shipment: BatchShipment) -> AuditEntity:
    return AuditEntity(
        type="batch_shipment",
        id=str(shipment.id),
        display_name=f"Shipment {shipment.id}",
        identifier=str(shipment.batch_id),
    )
