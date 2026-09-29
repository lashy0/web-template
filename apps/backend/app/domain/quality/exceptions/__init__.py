"""Quality domain errors with stable client-facing codes."""

from app.domain.quality.exceptions._defect_group import (
    DefectGroupArchivedError,
    DefectGroupCodeTakenError,
    DefectGroupHasActiveTypesError,
    DefectGroupInUseError,
)
from app.domain.quality.exceptions._defect_type import DefectTypeArchivedError, DefectTypeCodeTakenError
from app.domain.quality.exceptions._verification import (
    VerificationBatchArchivedError,
    VerificationKgNotFoundError,
    VerificationKgPackedError,
    VerificationKgScrappedError,
    VerificationSessionAlreadyRunningError,
    VerificationSessionIncompleteError,
    VerificationSessionNotFoundError,
    VerificationSessionNotRunningError,
    VerificationStepAlreadyCompletedError,
    VerificationStepAlreadyExistsError,
    VerificationStepInProgressError,
    VerificationStepNotFoundError,
    VerificationStepOutOfRangeError,
)

__all__ = (
    "DefectGroupArchivedError",
    "DefectGroupCodeTakenError",
    "DefectGroupHasActiveTypesError",
    "DefectGroupInUseError",
    "DefectTypeArchivedError",
    "DefectTypeCodeTakenError",
    "VerificationBatchArchivedError",
    "VerificationKgNotFoundError",
    "VerificationKgPackedError",
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
