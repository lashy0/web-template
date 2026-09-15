from app.modules.audit.types import AuditActor, AuditEntity
from app.shared.security import CurrentPrincipal

from .model import PakDevice


def audit_actor(actor: CurrentPrincipal) -> AuditActor:
    return AuditActor.user(actor.user_id, name=actor.name, login=actor.login)


def audit_entity(pak: PakDevice) -> AuditEntity:
    return AuditEntity(
        type="pak", id=str(pak.id), display_name=pak.code, identifier=pak.oauth_client_id
    )
