"""Litestar guards backed by the shared permission policy."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.handlers.base import BaseRouteHandler

from app.db import models as m
from app.lib.authorization.policy import PermissionPolicy

PermissionGuard = Callable[[ASGIConnection[Any, m.User, Any, Any], BaseRouteHandler], None]
AUTHORIZATION_POLICY_STATE_KEY = "authorization_policy"


def _policy_for_connection(connection: ASGIConnection[Any, m.User, Any, Any]) -> PermissionPolicy:
    """Resolve the policy from the application handling this request."""
    try:
        state = connection.app.state
    except (AttributeError, KeyError):
        return PermissionPolicy()

    policy = state.get(AUTHORIZATION_POLICY_STATE_KEY)
    if policy is None:
        return PermissionPolicy()

    if not isinstance(policy, PermissionPolicy):
        raise TypeError(
            f"Application state {AUTHORIZATION_POLICY_STATE_KEY!r} must contain a PermissionPolicy."
        )

    return policy


def requires_permission(permission: str) -> PermissionGuard:
    """Create a Litestar guard requiring one exact permission.

    Authentication is intentionally supplied by upstream middleware. The guard
    only consumes the trusted application user in the ASGI scope and never
    reads client-controlled claims.
    """
    permission_name = str(permission)

    def guard(
        connection: ASGIConnection[Any, m.User, Any, Any],
        _: BaseRouteHandler,
    ) -> None:
        scope = cast("dict[str, object]", connection.scope)
        user = scope.get("user")

        if not isinstance(user, m.User):
            raise NotAuthorizedException(detail="Authentication required.")

        policy = _policy_for_connection(connection)
        if not policy.has_permission(user.role, permission_name):
            raise PermissionDeniedException(
                detail=f"Permission required: {permission_name}.",
            )

    return guard


__all__ = ("AUTHORIZATION_POLICY_STATE_KEY", "PermissionGuard", "requires_permission")
