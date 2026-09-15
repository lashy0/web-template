"""Compatibility import; HTTP ownership is contexts.identity.users."""

from app.contexts.identity.users.router import router

__all__ = ["router"]
