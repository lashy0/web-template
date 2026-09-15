from app.core.exceptions import AppError, ConflictError, NotFoundError


class VerificationError(AppError):
    default_message = ""


class VerificationConflictError(VerificationError, ConflictError):
    code = "verification_conflict"


class VerificationSessionNotFoundError(VerificationError, NotFoundError):
    code = "verification_session_not_found"


class VerificationSessionAlreadyRunningError(VerificationError, ConflictError):
    code = "verification_session_already_running"


class VerificationSessionNotRunningError(VerificationError, ConflictError):
    code = "verification_session_not_running"


class VerificationSessionIncompleteError(VerificationError, ConflictError):
    code = "verification_session_incomplete"


class VerificationKgNotFoundError(VerificationError, NotFoundError):
    code = "verification_kg_not_found"


class VerificationKgNotReadyError(VerificationError, ConflictError):
    code = "verification_kg_not_ready"


class VerificationStepNotFoundError(VerificationError, NotFoundError):
    code = "verification_step_not_found"


class VerificationStepAlreadyExistsError(VerificationError, ConflictError):
    code = "verification_step_already_exists"


class VerificationStepAlreadyCompletedError(VerificationError, ConflictError):
    code = "verification_step_already_completed"


class VerificationStepOutOfRangeError(VerificationError, ConflictError):
    code = "verification_step_out_of_range"


class VerificationStepInProgressError(VerificationError, ConflictError):
    code = "verification_step_in_progress"
