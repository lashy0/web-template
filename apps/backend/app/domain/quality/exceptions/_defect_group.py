"""Defect group errors."""

from app.lib.exceptions import ApplicationConflictError


class DefectGroupCodeTakenError(ApplicationConflictError):
    """Another defect group already has the code (HTTP 409)."""

    code = "defect_group_code_taken"
    detail = "Defect group code is already registered."


class DefectGroupArchivedError(ApplicationConflictError):
    """The defect group is archived and cannot be modified (HTTP 409)."""

    code = "defect_group_archived"
    detail = "Archived defect group cannot be modified."


class DefectGroupHasActiveTypesError(ApplicationConflictError):
    """The defect group still has types that are not archived (HTTP 409)."""

    code = "defect_group_has_active_types"
    detail = "Archive the defect types of the group first."


class DefectGroupInUseError(ApplicationConflictError):
    """Defect types, PAK checks or verification steps refer to the group, so it cannot be deleted (HTTP 409)."""

    code = "defect_group_in_use"
    detail = "Defect group has defect types or verification history; archive it instead."
