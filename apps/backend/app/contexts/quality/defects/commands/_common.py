from app.audit.types import AuditActor, AuditEntity
from app.shared.security import CurrentPrincipal

from ..model import DefectGroup, DefectType


def audit_actor(actor: CurrentPrincipal) -> AuditActor:
    return AuditActor.user(actor.user_id, name=actor.name, login=actor.login)


def group_entity(item: DefectGroup) -> AuditEntity:
    return AuditEntity(
        type="defect_group", id=str(item.id), display_name=item.name, identifier=item.code
    )


def type_entity(item: DefectType) -> AuditEntity:
    return AuditEntity(
        type="defect_type", id=str(item.id), display_name=item.name, identifier=item.code
    )
