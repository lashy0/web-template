"""Permission identifiers owned by the PAK domain."""

from enum import StrEnum


class PakPermission(StrEnum):
    """Capabilities for managing PAK devices."""

    READ = "paks.read"
    CREATE = "paks.create"
    UPDATE = "paks.update"

    SET_ACTIVE = "paks.set_active"

    ARCHIVE = "paks.archive"

    DELETE = "paks.delete"
    READ_ACCESS_KEY = "paks.read_access_key"
    ROTATE_ACCESS_KEY = "paks.rotate_access_key"


__all__ = ("PakPermission",)
