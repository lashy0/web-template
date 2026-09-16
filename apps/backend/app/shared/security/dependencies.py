"""Stable authentication and authorization dependencies for HTTP adapters.

The dependency functions in this module are deliberately provider-agnostic:
they express what an HTTP handler needs, rather than how a browser session is
verified or how a local user is found. ``app.api`` installs the concrete
resolver when it builds the FastAPI application.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends

from app.shared.security.exceptions import ForbiddenError
from app.shared.security.permissions import Permission
from app.shared.security.principal import CurrentPrincipal

type PermissionDependency = Callable[..., Awaitable[CurrentPrincipal]]


async def get_current_principal() -> CurrentPrincipal:
    """Resolve the authenticated user through the composition-installed adapter."""

    raise RuntimeError("Authentication dependency is not configured")


CurrentPrincipalDep = Annotated[CurrentPrincipal, Depends(get_current_principal)]


def require_permission(permission: Permission) -> PermissionDependency:
    """Require a permission from the current authentication context."""

    async def dependency(principal: CurrentPrincipalDep) -> CurrentPrincipal:
        if not principal.has_permission(permission):
            raise ForbiddenError
        return principal

    return dependency


__all__ = [
    "CurrentPrincipalDep",
    "PermissionDependency",
    "get_current_principal",
    "require_permission",
]
