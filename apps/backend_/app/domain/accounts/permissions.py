"""Permission identifiers owned by the accounts domain."""

from enum import StrEnum


class UserPermission(StrEnum):
    """Capabilities for managing application users."""

    READ = "users.read"
    CREATE = "users.create"
    UPDATE = "users.update"
    DELETE = "users.delete"


__all__ = ("UserPermission",)
