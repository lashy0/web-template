from enum import StrEnum
from typing import Final

from app.auth.roles import Role


class Permission(StrEnum):
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_SET_PASSWORD = "user:set_password"
    USER_SET_ACTIVE = "user:set_active"
    USER_ARCHIVE = "user:archive"
    USER_DELETE = "user:delete"

    AUDIT_READ = "audit:read"


ROLE_PERMISSIONS: Final[dict[Role, frozenset[Permission]]] = {
    Role.ADMINISTRATOR: frozenset(Permission),
    Role.MANAGER: frozenset(),
    Role.ENGINEER: frozenset(),
    Role.PACKER: frozenset(),
    Role.OPERATOR: frozenset(),
}


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def role_has_permission(role: Role, permission: Permission) -> bool:
    return permission in permissions_for_role(role)
