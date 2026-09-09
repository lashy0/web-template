from app.auth.principal import CurrentPrincipal
from app.modules.audit.types import AuditActor, AuditEntity

from ..models import ProductionOrder


def actor_identity(actor: CurrentPrincipal) -> AuditActor:
    return AuditActor.user(
        actor.user_id,
        name=actor.name,
        login=actor.login,
    )


def order_entity(item: ProductionOrder) -> AuditEntity:
    return AuditEntity(
        type="production_order",
        id=str(item.id),
        display_name=item.name,
        identifier=str(item.id),
    )
