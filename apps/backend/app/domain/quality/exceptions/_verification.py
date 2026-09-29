"""Verification errors: the KG unit, the session and its steps."""

from app.lib.exceptions import ApplicationConflictError, ApplicationNotFoundError


class VerificationKgNotFoundError(ApplicationNotFoundError):
    """No KG unit has the DevEUI the PAK reported (HTTP 404)."""

    code = "verification_kg_not_found"
    detail = "KG unit not found."


class VerificationKgScrappedError(ApplicationConflictError):
    """The KG unit is scrapped and cannot be verified (HTTP 409)."""

    code = "verification_kg_scrapped"
    detail = "Scrapped KG unit cannot be verified."


class VerificationKgPackedError(ApplicationConflictError):
    """The KG unit is packed or shipped, so an OTK-line PAK cannot verify it (HTTP 409)."""

    code = "verification_kg_packed"
    detail = "Packed or shipped KG unit cannot be verified on an OTK-line PAK."


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
