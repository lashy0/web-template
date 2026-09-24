"""Application-level composition of production authorization grants."""

from app.db.enums import UserRole
from app.domain.accounts.permissions import UserPermission
from app.domain.pak.permissions import PakPermission
from app.domain.production.permissions import (
    KgPrefixPermission,
    KgVersionPermission,
    ProductionOrderPermission,
)
from app.lib.authorization import PermissionPolicy


def create_authorization_policy() -> PermissionPolicy:
    """Build the production policy with explicit role assignments."""
    return PermissionPolicy(
        {
            UserRole.ADMINISTRATOR: {
                *UserPermission,
                *PakPermission,
                *ProductionOrderPermission,
                *KgPrefixPermission,
                *KgVersionPermission,
            },
            UserRole.MANAGER: {
                *ProductionOrderPermission,
                KgPrefixPermission.READ,
                KgVersionPermission.READ,
            },
            UserRole.ENGINEER: set(),
            UserRole.PACKER: set(),
            UserRole.OPERATOR: set(),
        }
    )


__all__ = ("create_authorization_policy",)
