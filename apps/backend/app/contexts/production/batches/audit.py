from app.modules.audit.types import AuditActor, AuditEntity
from app.shared.security import CurrentPrincipal

from .model import Batch


def audit_actor(actor: CurrentPrincipal) -> AuditActor:
    return AuditActor.user(actor.user_id, name=actor.name, login=actor.login)


def batch_entity(batch: Batch) -> AuditEntity:
    return AuditEntity(
        type="batch", id=str(batch.id), display_name=batch.name, identifier=str(batch.id)
    )


def receipt_entity(receipt: object) -> AuditEntity:
    return AuditEntity(
        type="batch_receipt",
        id=str(receipt.id),  # type: ignore[attr-defined]
        display_name=f"Receipt {receipt.id}",  # type: ignore[attr-defined]
        identifier=str(receipt.batch_id),  # type: ignore[attr-defined]
    )


def shipment_entity(shipment: object) -> AuditEntity:
    return AuditEntity(
        type="batch_shipment",
        id=str(shipment.id),  # type: ignore[attr-defined]
        display_name=f"Shipment {shipment.id}",  # type: ignore[attr-defined]
        identifier=str(shipment.batch_id),  # type: ignore[attr-defined]
    )
