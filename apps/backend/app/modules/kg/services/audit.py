from app.auth.principal import CurrentPrincipal
from app.modules.audit.types import AuditActor, AuditEntity

from ..models import KgDevEuiPrefix, KgUnit, KgVersion


def actor_identity(actor: CurrentPrincipal) -> AuditActor:
    return AuditActor.user(
        actor.user_id,
        name=actor.name,
        login=actor.login,
    )


def unit_entity(kg: KgUnit) -> AuditEntity:
    return AuditEntity(
        type="kg",
        id=kg.dev_eui,
        display_name=kg.dev_eui,
        identifier=kg.dev_eui,
    )


def prefix_entity(item: KgDevEuiPrefix) -> AuditEntity:
    return AuditEntity(
        type="kg_dev_eui_prefix",
        id=item.prefix,
        display_name=item.name or item.prefix,
        identifier=item.prefix,
    )


def version_entity(item: KgVersion) -> AuditEntity:
    return AuditEntity(
        type="kg_version",
        id=str(item.id),
        display_name=item.name,
        identifier=item.code,
    )
