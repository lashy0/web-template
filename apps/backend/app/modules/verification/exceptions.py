from app.core.exceptions import AppError


class VerificationError(AppError):
    """Base exception for verification domain failures."""

    default_message = ""


class VerificationSessionNotFoundError(VerificationError):
    """The requested verification session does not exist."""

    code = "verification_session_not_found"


class VerificationSessionAlreadyRunningError(VerificationError):
    """A running verification session already exists for the KG."""

    code = "verification_session_already_running"


class VerificationSessionNotRunningError(VerificationError):
    """The verification session is no longer running."""

    code = "verification_session_not_running"


class VerificationSessionIncompleteError(VerificationError):
    """The verification session cannot be completed yet."""

    code = "verification_session_incomplete"


class VerificationKgNotFoundError(VerificationError):
    """The requested KG unit does not exist."""

    code = "verification_kg_not_found"


class VerificationKgNotReadyError(VerificationError):
    """The KG unit is not ready for verification."""

    code = "verification_kg_not_ready"


class VerificationStepNotFoundError(VerificationError):
    """The requested verification step does not exist."""

    code = "verification_step_not_found"


class VerificationStepAlreadyExistsError(VerificationError):
    """The verification step already exists in the session."""

    code = "verification_step_already_exists"


class VerificationStepAlreadyCompletedError(VerificationError):
    """The verification step has already been completed."""

    code = "verification_step_already_completed"


class VerificationStepOutOfRangeError(VerificationError):
    """The verification step number is outside the session step range."""

    code = "verification_step_out_of_range"


class VerificationStepInProgressError(VerificationError):
    """Another verification step is already running in the session."""

    code = "verification_step_in_progress"
