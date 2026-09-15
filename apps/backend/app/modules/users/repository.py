"""Compatibility import; repository ownership is contexts.identity.users."""

from app.contexts.identity.users.repository import UserRepository

__all__ = ["UserRepository"]
