from app.modules.audit.types import AuditActor, AuditEntity
from app.shared.security import CurrentPrincipal

from .model import Batch


def audit_actor(actor: CurrentPrincipal) -> AuditActor:
    return AuditActor.user(actor.user_id, name=actor.name, login=actor.login)


def batch_entity(batch: Batch) -> AuditEntity:
    return AuditEntity(
        type="batch", id=str(batch.id), display_name=batch.name, identifier=str(batch.id)
    )
