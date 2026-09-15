"""Compatibility access to the canonical, explicitly installed registry.

This module must not compose or install feature permissions.  The composition
root owns the application permission catalogue.
"""

from app.shared.security.permissions import Permission, permissions_for_role, role_has_permission

__all__ = [
    "Permission",
    "permissions_for_role",
    "role_has_permission",
]
