"""Compatibility public security vocabulary for new contexts."""

from app.auth.exceptions import ForbiddenError, IdentityNotFoundError
from app.shared.security.contracts import AuthSession, Identity, IdentityProvider, SessionProvider
from app.shared.security.permissions import (
    ALL_PERMISSIONS,
    ROLE_PERMISSIONS,
    Permission,
    permissions_for_role,
    role_has_permission,
)
from app.shared.security.principal import CurrentPrincipal
from app.shared.security.roles import Role

__all__ = [
    "ALL_PERMISSIONS",
    "AuthSession",
    "CurrentPrincipal",
    "ForbiddenError",
    "Identity",
    "IdentityNotFoundError",
    "IdentityProvider",
    "Permission",
    "ROLE_PERMISSIONS",
    "Role",
    "SessionProvider",
    "permissions_for_role",
    "role_has_permission",
]
