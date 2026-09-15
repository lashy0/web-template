from app.modules.audit.types import AuditActor, AuditEntity
from app.shared.security import CurrentPrincipal

from .model import User


def audit_actor(actor: CurrentPrincipal | None) -> AuditActor:
    return (
        AuditActor.user(actor.user_id, name=actor.name, login=actor.login)
        if actor
        else AuditActor.system()
    )


def audit_entity(user: User) -> AuditEntity:
    return AuditEntity.user(user.id, name=user.name, login=user.identity_login)
