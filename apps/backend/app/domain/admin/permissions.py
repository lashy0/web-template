"""Permission identifiers owned by the admin domain."""

from enum import StrEnum


class AuditPermission(StrEnum):
    """Capabilities for the audit log; entries are written by the actions themselves."""

    READ = "audit.read"


__all__ = ("AuditPermission",)
