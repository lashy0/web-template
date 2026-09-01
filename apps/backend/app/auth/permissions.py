from enum import StrEnum
from typing import Final

from app.auth.roles import Role
from app.modules.audit.permissions import AuditPermission
from app.modules.pak.permissions import PakPermission
from app.modules.users.permissions import UserPermission
from app.modules.kg.permissions import KgPermission
from app.modules.batch.permissions import BatchPermission
from app.modules.verification.permissions import VerificationPermission


type Permission = StrEnum

ALL_PERMISSIONS: Final[frozenset[Permission]] = frozenset(
    (
        *UserPermission,
        *PakPermission,
        *AuditPermission,
        *KgPermission,
        *BatchPermission,
        *VerificationPermission,
    )
)

MANAGER_PERMISSIONS: Final[frozenset[Permission]] = frozenset(
    (
        BatchPermission.CREATE,
        BatchPermission.READ,
        BatchPermission.UPDATE,
        BatchPermission.ARCHIVE,
        BatchPermission.COMPLETE,
        BatchPermission.DELETE,

        BatchPermission.RECEIPT_CREATE,
        BatchPermission.RECEIPT_UPDATE,
        BatchPermission.RECEIPT_VOID,

        BatchPermission.SHIPMENT_CREATE,
        BatchPermission.SHIPMENT_UPDATE,
        BatchPermission.SHIPMENT_COMPLETE,
        BatchPermission.SHIPMENT_VOID,

        KgPermission.READ,
        KgPermission.PREFIX_READ,

        VerificationPermission.READ,
    )
)

ENGINEER_PERMISSIONS: Final[frozenset[Permission]] = frozenset(
    (
        KgPermission.READ,
        VerificationPermission.READ,
    )
)


ROLE_PERMISSIONS: Final[dict[Role, frozenset[Permission]]] = {
    Role.ADMINISTRATOR: ALL_PERMISSIONS,
    Role.MANAGER: MANAGER_PERMISSIONS,
    Role.ENGINEER: ENGINEER_PERMISSIONS,
    Role.PACKER: frozenset(),
    Role.OPERATOR: frozenset(),
}


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def role_has_permission(role: Role, permission: Permission) -> bool:
    return permission in permissions_for_role(role)
