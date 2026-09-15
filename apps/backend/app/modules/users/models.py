"""Compatibility import; User ownership is contexts.identity.users."""

from app.contexts.identity.users.model import ROLE_DB_TYPE, User

__all__ = ["ROLE_DB_TYPE", "User"]
