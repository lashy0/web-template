"""Account domain dependencies."""

from __future__ import annotations

from app.domain.accounts.services import UserService
from app.lib.deps import create_service_provider

provide_users_service = create_service_provider(
    UserService,
    error_messages={
        "duplicate_key": "User already exists.",
        "integrity": "User operation failed.",
    },
)

__all__ = ("provide_users_service",)
