"""Compatibility exports for the existing permission registry."""

from app.auth.permissions import (
    ALL_PERMISSIONS,
    ROLE_PERMISSIONS,
    Permission,
    permissions_for_role,
    role_has_permission,
)

__all__ = [
    "ALL_PERMISSIONS",
    "Permission",
    "ROLE_PERMISSIONS",
    "permissions_for_role",
    "role_has_permission",
]
