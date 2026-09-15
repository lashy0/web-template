"""Security vocabulary shared by application contexts.

This package intentionally has no dependency on ``app.auth`` or FastAPI.
"""

from app.shared.security.contracts import Identity
from app.shared.security.exceptions import ForbiddenError, IdentityNotFoundError
from app.shared.security.permissions import (
    Permission,
    PermissionRegistry,
    install_permission_registry,
    permission_registry,
    permissions_for_role,
    role_has_permission,
)
from app.shared.security.principal import CurrentPrincipal
from app.shared.security.roles import Role

__all__ = [
    "CurrentPrincipal",
    "ForbiddenError",
    "Identity",
    "IdentityNotFoundError",
    "Permission",
    "PermissionRegistry",
    "Role",
    "install_permission_registry",
    "permission_registry",
    "permissions_for_role",
    "role_has_permission",
]
