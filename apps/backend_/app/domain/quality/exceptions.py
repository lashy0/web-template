"""Quality domain errors with stable client-facing codes."""

from app.lib.exceptions import ApplicationConflictError, ApplicationNotFoundError


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


class DefectTypeCodeTakenError(ApplicationConflictError):
    """Another defect type already has the code (HTTP 409)."""

    code = "defect_type_code_taken"
    detail = "Defect type code is already registered."


class DefectTypeArchivedError(ApplicationConflictError):
    """The defect type is archived and cannot be modified (HTTP 409)."""

    code = "defect_type_archived"
    detail = "Archived defect type cannot be modified."


class VerificationKgNotFoundError(ApplicationNotFoundError):
    """No KG unit has the DevEUI the PAK reported (HTTP 404)."""

    code = "verification_kg_not_found"
    detail = "KG unit not found."


class VerificationKgScrappedError(ApplicationConflictError):
    """The KG unit is scrapped and cannot be verified (HTTP 409)."""

    code = "verification_kg_scrapped"
    detail = "Scrapped KG unit cannot be verified."


class VerificationBatchArchivedError(ApplicationConflictError):
    """The batch of the KG unit is archived, so the unit cannot be verified (HTTP 409)."""

    code = "verification_batch_archived"
    detail = "KG unit of an archived batch cannot be verified."


class VerificationSessionNotFoundError(ApplicationNotFoundError):
    """The session does not exist or belongs to another PAK (HTTP 404)."""

    code = "verification_session_not_found"
    detail = "Verification session not found."


class VerificationSessionAlreadyRunningError(ApplicationConflictError):
    """The KG unit is being verified in another PAK slot (HTTP 409)."""

    code = "verification_session_already_running"
    detail = "KG unit is being verified in another PAK slot."


class VerificationSessionNotRunningError(ApplicationConflictError):
    """The session is finished and accepts no more reports (HTTP 409)."""

    code = "verification_session_not_running"
    detail = "Verification session is already finished."


class VerificationSessionIncompleteError(ApplicationConflictError):
    """The session cannot finish so: a step is running, or not every step passed (HTTP 409)."""

    code = "verification_session_incomplete"
    detail = "Verification session has a running step or steps that did not pass."


class VerificationStepNotFoundError(ApplicationNotFoundError):
    """The session has no step with the number (HTTP 404)."""

    code = "verification_step_not_found"
    detail = "Verification step not found."


class VerificationStepOutOfRangeError(ApplicationConflictError):
    """The step number exceeds the session's number of steps (HTTP 409)."""

    code = "verification_step_out_of_range"
    detail = "Step number exceeds the number of steps of the session."


class VerificationStepAlreadyExistsError(ApplicationConflictError):
    """The step number was started with another check (HTTP 409)."""

    code = "verification_step_already_exists"
    detail = "Verification step was already started with another check."


class VerificationStepInProgressError(ApplicationConflictError):
    """Another step of the session is still running (HTTP 409)."""

    code = "verification_step_in_progress"
    detail = "Another step of the session is still running."


class VerificationStepAlreadyCompletedError(ApplicationConflictError):
    """The step was already completed with another result (HTTP 409)."""

    code = "verification_step_already_completed"
    detail = "Verification step was already completed with another result."


__all__ = (
    "DefectGroupArchivedError",
    "DefectGroupCodeTakenError",
    "DefectGroupHasActiveTypesError",
    "DefectGroupInUseError",
    "DefectTypeArchivedError",
    "DefectTypeCodeTakenError",
    "VerificationBatchArchivedError",
    "VerificationKgNotFoundError",
    "VerificationKgScrappedError",
    "VerificationSessionAlreadyRunningError",
    "VerificationSessionIncompleteError",
    "VerificationSessionNotFoundError",
    "VerificationSessionNotRunningError",
    "VerificationStepAlreadyCompletedError",
    "VerificationStepAlreadyExistsError",
    "VerificationStepInProgressError",
    "VerificationStepNotFoundError",
    "VerificationStepOutOfRangeError",
)
