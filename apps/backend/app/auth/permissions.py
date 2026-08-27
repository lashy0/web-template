from enum import StrEnum
from typing import Final

from app.auth.roles import Role
from app.modules.audit.permissions import AuditPermission
from app.modules.pak.permissions import PakPermission
from app.modules.users.permissions import UserPermission

type Permission = StrEnum

ALL_PERMISSIONS: Final[frozenset[Permission]] = frozenset(
    (*UserPermission, *PakPermission, *AuditPermission)
)


ROLE_PERMISSIONS: Final[dict[Role, frozenset[Permission]]] = {
    Role.ADMINISTRATOR: ALL_PERMISSIONS,
    Role.MANAGER: frozenset(),
    Role.ENGINEER: frozenset(),
    Role.PACKER: frozenset(),
    Role.OPERATOR: frozenset(),
}


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def role_has_permission(role: Role, permission: Permission) -> bool:
    return permission in permissions_for_role(role)
