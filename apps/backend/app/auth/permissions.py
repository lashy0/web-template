"""Legacy authentication imports for the bootstrap-composed registry."""

from app.bootstrap.permissions import (
    ALL_PERMISSIONS,
    ENGINEER_PERMISSIONS,
    MANAGER_PERMISSIONS,
    ROLE_PERMISSIONS,
)
from app.shared.security.permissions import Permission, permissions_for_role, role_has_permission

__all__ = [
    "ALL_PERMISSIONS",
    "ENGINEER_PERMISSIONS",
    "MANAGER_PERMISSIONS",
    "Permission",
    "ROLE_PERMISSIONS",
    "permissions_for_role",
    "role_has_permission",
]
