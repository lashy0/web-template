"""Compatibility package; user ownership is contexts.identity.users."""

from .services import BOOTSTRAP_ADMIN_USER_ID, UserManagementService

__all__ = ["BOOTSTRAP_ADMIN_USER_ID", "UserManagementService"]
