"""Defect type errors."""

from app.lib.exceptions import ApplicationConflictError


class DefectTypeCodeTakenError(ApplicationConflictError):
    """Another defect type already has the code (HTTP 409)."""

    code = "defect_type_code_taken"
    detail = "Defect type code is already registered."


class DefectTypeArchivedError(ApplicationConflictError):
    """The defect type is archived and cannot be modified (HTTP 409)."""

    code = "defect_type_archived"
    detail = "Archived defect type cannot be modified."
