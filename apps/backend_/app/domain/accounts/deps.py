"""Account domain dependencies."""

from __future__ import annotations

from typing import Any, cast

from litestar import Request
from litestar.exceptions import NotAuthorizedException

from app.db import models as m
from app.domain.accounts.services import UserService
from app.lib.deps import create_service_provider

provide_users_service = create_service_provider(
    UserService,
    error_messages={
        "duplicate_key": "User already exists.",
        "integrity": "User operation failed.",
    },
)


def provide_current_user(request: Request[Any, Any, Any]) -> m.User:
    """Return the authenticated application user from the request context."""
    user = cast("object", request.user)

    if not isinstance(user, m.User):
        raise NotAuthorizedException(detail="Authentication required.")

    return user


__all__ = ("provide_current_user", "provide_users_service")
