from app.auth.principal import CurrentPrincipal
from app.modules.audit.types import AuditActor, AuditEntity

from ..models import PakDevice


def _audit_actor(actor: CurrentPrincipal) -> AuditActor:
    return AuditActor.user(
        actor.user_id,
        name=actor.name,
        login=actor.login,
    )


def _audit_entity(pak: PakDevice) -> AuditEntity:
    return AuditEntity(
        type="pak",
        id=str(pak.id),
        display_name=pak.code,
        identifier=pak.oauth_client_id,
    )
