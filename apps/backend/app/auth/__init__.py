from app.auth.contracts import (
    AuthSession,
    Identity,
    IdentityProvider,
    SessionProvider,
)
from app.auth.exceptions import (
    AuthenticationError,
    AuthError,
    AuthorizationError,
    ForbiddenError,
    IdentityAlreadyExistsError,
    IdentityNotFoundError,
    IdentityProviderError,
    IdentityProviderUnavailableError,
    InvalidSessionError,
)
from app.auth.permissions import (
    ALL_PERMISSIONS,
    ROLE_PERMISSIONS,
    Permission,
    permissions_for_role,
    role_has_permission,
)
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role

__all__ = [
    "AuthError",
    "AuthSession",
    "AuthenticationError",
    "AuthorizationError",
    "CurrentPrincipal",
    "ForbiddenError",
    "Identity",
    "IdentityAlreadyExistsError",
    "IdentityNotFoundError",
    "IdentityProvider",
    "IdentityProviderError",
    "IdentityProviderUnavailableError",
    "InvalidSessionError",
    "ALL_PERMISSIONS",
    "Permission",
    "ROLE_PERMISSIONS",
    "Role",
    "SessionProvider",
    "permissions_for_role",
    "role_has_permission",
]
