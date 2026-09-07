from app.auth.principal import CurrentPrincipal
from app.modules.audit.types import AuditActor, AuditEntity

from ..models import DefectGroup, DefectType


def _audit_actor(actor: CurrentPrincipal) -> AuditActor:
    return AuditActor.user(
        actor.user_id,
        name=actor.name,
        login=actor.login,
    )


def _group_audit_entity(group: DefectGroup) -> AuditEntity:
    return AuditEntity(
        type="defect_group",
        id=str(group.id),
        display_name=group.name,
        identifier=group.code,
    )


def _type_audit_entity(defect_type: DefectType) -> AuditEntity:
    return AuditEntity(
        type="defect_type",
        id=str(defect_type.id),
        display_name=defect_type.name,
        identifier=defect_type.code,
    )
