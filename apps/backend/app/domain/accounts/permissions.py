"""Permission identifiers owned by the accounts domain."""

from enum import StrEnum


class UserPermission(StrEnum):
    """Capabilities for managing application users."""

    READ = "users.read"
    CREATE = "users.create"
    UPDATE = "users.update"

    ASSIGN_ROLE = "users.assign_role"

    SET_PASSWORD = "users.set_password"
    SET_ACTIVE = "users.set_active"

    ARCHIVE = "users.archive"

    DELETE = "users.delete"


__all__ = ("UserPermission",)
