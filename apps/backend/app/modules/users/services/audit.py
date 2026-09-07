from app.modules.audit.types import AuditEntity

from ..models import User


def _audit_entity(user: User) -> AuditEntity:
    return AuditEntity.user(
        user.id,
        name=user.name,
        login=user.identity_login,
    )
