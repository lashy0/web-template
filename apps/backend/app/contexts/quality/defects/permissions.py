"""Defect permission vocabulary owned by the quality context."""

from enum import StrEnum


class DefectPermission(StrEnum):
    CREATE = "defect:create"
    READ = "defect:read"
    UPDATE = "defect:update"
    ARCHIVE = "defect:archive"
    DELETE = "defect:delete"
