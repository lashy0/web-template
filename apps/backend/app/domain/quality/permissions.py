"""Permission identifiers owned by the quality domain."""

from enum import StrEnum


class DefectPermission(StrEnum):
    """Capabilities for managing the defect catalog."""

    READ = "defects.read"
    CREATE = "defects.create"
    UPDATE = "defects.update"

    ARCHIVE = "defects.archive"

    DELETE = "defects.delete"


class VerificationPermission(StrEnum):
    """Capabilities for viewing verification history and the PAK check catalog.

    PAKs write both through the machine API; users only read them.
    """

    READ = "verification.read"


__all__ = ("DefectPermission", "VerificationPermission")
