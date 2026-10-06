"""Shared permission-based authorization primitives."""

from app.lib.authorization.guards import granted_permissions, requires_permission
from app.lib.authorization.policy import (
    PermissionPolicy,
    has_permission,
    has_permission_in,
    permissions_for_role,
)

__all__ = (
    "PermissionPolicy",
    "granted_permissions",
    "has_permission",
    "has_permission_in",
    "permissions_for_role",
    "requires_permission",
)
