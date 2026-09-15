from enum import StrEnum
from typing import Final

from app.auth.roles import Role
from app.contexts.equipment.pak.permissions import PakPermission
from app.contexts.quality.verification.permissions import VerificationPermission
from app.modules.audit.permissions import AuditPermission
from app.modules.batch.permissions import BatchPermission
from app.modules.defects.permissions import DefectPermission
from app.modules.kg.permissions import KgPermission
from app.modules.production_order.permissions import ProductionOrderPermission
from app.modules.users.permissions import UserPermission

type Permission = StrEnum

ALL_PERMISSIONS: Final[frozenset[Permission]] = frozenset(
    (
        *UserPermission,
        *PakPermission,
        *AuditPermission,
        *KgPermission,
        *BatchPermission,
        *ProductionOrderPermission,
        *VerificationPermission,
        *DefectPermission,
    )
)

MANAGER_PERMISSIONS: Final[frozenset[Permission]] = frozenset(
    (
        *ProductionOrderPermission,
        BatchPermission.ASSIGN_PRODUCTION_ORDER,
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
        KgPermission.VERSION_READ,
        VerificationPermission.READ,
        DefectPermission.READ,
    )
)

ENGINEER_PERMISSIONS: Final[frozenset[Permission]] = frozenset(
    (
        KgPermission.READ,
        VerificationPermission.READ,
        DefectPermission.READ,
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
