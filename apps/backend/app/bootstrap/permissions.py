"""Composition of feature permission vocabularies.

This is deliberately the one place that knows the complete application
permission surface. Neither shared security nor authentication imports feature
contexts to assemble a registry.
"""

from typing import Final

from app.audit.permissions import AuditPermission
from app.contexts.equipment.pak.permissions import PakPermission
from app.contexts.identity.users.permissions import UserPermission
from app.contexts.production.batches.permissions import BatchPermission
from app.contexts.production.kg.permissions import KgPermission
from app.contexts.production.production_orders.permissions import ProductionOrderPermission
from app.contexts.quality.defects.permissions import DefectPermission
from app.contexts.quality.verification.permissions import VerificationPermission
from app.shared.security import Permission, PermissionRegistry, Role

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
    (KgPermission.READ, VerificationPermission.READ, DefectPermission.READ)
)
ROLE_PERMISSIONS: Final[dict[Role, frozenset[Permission]]] = {
    Role.ADMINISTRATOR: ALL_PERMISSIONS,
    Role.MANAGER: MANAGER_PERMISSIONS,
    Role.ENGINEER: ENGINEER_PERMISSIONS,
    Role.PACKER: frozenset(),
    Role.OPERATOR: frozenset(),
}


def compose_permission_registry() -> PermissionRegistry:
    """Build the application permission registry at the composition root.

    Building is deliberately side-effect free: process-wide installation is an
    explicit startup responsibility (see ``app.main.create_app``).
    """

    return PermissionRegistry(ALL_PERMISSIONS, ROLE_PERMISSIONS)
