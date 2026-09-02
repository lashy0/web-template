from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.auth.exceptions import (
    AccountDisabledError,
    ForbiddenError,
    IdentityAlreadyExistsError,
    IdentityNotFoundError,
    IdentityProviderUnavailableError,
    InvalidMachineCredentialsError,
    InvalidSessionError,
    OAuthClientAlreadyExistsError,
    OAuthClientNotFoundError,
    OAuthProviderUnavailableError,
    UserNotProvisionedError,
)
from app.core.exceptions import AppError
from app.modules.batch.exceptions import BatchNotFoundError
from app.modules.kg.exceptions import KgAlreadyExistsError, KgCannotBeDeletedError, KgNotFoundError
from app.modules.pak.exceptions import (
    InvalidMachineAccessTokenError,
    PakAccessKeyConfigurationError,
    PakAlreadyExistsError,
    PakCannotBeDeletedError,
    PakNotFoundError,
    PakProvisioningError,
    PakTestNotFoundError,
)
from app.modules.users.exceptions import UserNotFoundError, UserProvisioningError
from app.modules.verification.exceptions import (
    VerificationKgNotFoundError,
    VerificationKgNotReadyError,
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


def _error(request: Request, error: AppError, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": error.code,
            "message": str(error) or error.code.replace("_", " "),
            "request_id": getattr(request.state, "request_id", ""),
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    mappings: list[tuple[type[AppError], int]] = [
        (InvalidSessionError, status.HTTP_401_UNAUTHORIZED),
        (InvalidMachineAccessTokenError, status.HTTP_401_UNAUTHORIZED),
        (InvalidMachineCredentialsError, status.HTTP_401_UNAUTHORIZED),
        (AccountDisabledError, status.HTTP_403_FORBIDDEN),
        (UserNotProvisionedError, status.HTTP_403_FORBIDDEN),
        (ForbiddenError, status.HTTP_403_FORBIDDEN),
        (IdentityAlreadyExistsError, status.HTTP_409_CONFLICT),
        (OAuthClientAlreadyExistsError, status.HTTP_409_CONFLICT),
        (UserProvisioningError, status.HTTP_503_SERVICE_UNAVAILABLE),
        (IdentityNotFoundError, status.HTTP_404_NOT_FOUND),
        (OAuthClientNotFoundError, status.HTTP_404_NOT_FOUND),
        (UserNotFoundError, status.HTTP_404_NOT_FOUND),
        (BatchNotFoundError, status.HTTP_404_NOT_FOUND),
        (KgNotFoundError, status.HTTP_404_NOT_FOUND),
        (PakNotFoundError, status.HTTP_404_NOT_FOUND),
        (PakTestNotFoundError, status.HTTP_404_NOT_FOUND),
        (KgAlreadyExistsError, status.HTTP_409_CONFLICT),
        (KgCannotBeDeletedError, status.HTTP_409_CONFLICT),
        (PakAlreadyExistsError, status.HTTP_409_CONFLICT),
        (PakAccessKeyConfigurationError, status.HTTP_503_SERVICE_UNAVAILABLE),
        (PakProvisioningError, status.HTTP_503_SERVICE_UNAVAILABLE),
        (PakCannotBeDeletedError, status.HTTP_409_CONFLICT),
        (IdentityProviderUnavailableError, status.HTTP_503_SERVICE_UNAVAILABLE),
        (OAuthProviderUnavailableError, status.HTTP_503_SERVICE_UNAVAILABLE),
        (VerificationSessionNotFoundError, status.HTTP_404_NOT_FOUND),
        (VerificationStepNotFoundError, status.HTTP_404_NOT_FOUND),
        (VerificationKgNotFoundError, status.HTTP_404_NOT_FOUND),
        (VerificationKgNotReadyError, status.HTTP_409_CONFLICT),
        (VerificationSessionAlreadyRunningError, status.HTTP_409_CONFLICT),
        (VerificationSessionNotRunningError, status.HTTP_409_CONFLICT),
        (VerificationSessionIncompleteError, status.HTTP_409_CONFLICT),
        (VerificationStepAlreadyExistsError, status.HTTP_409_CONFLICT),
        (VerificationStepAlreadyCompletedError, status.HTTP_409_CONFLICT),
        (VerificationStepInProgressError, status.HTTP_409_CONFLICT),
        (VerificationStepOutOfRangeError, status.HTTP_409_CONFLICT),
    ]
    for exception, status_code in mappings:
        app.add_exception_handler(
            exception,
            lambda request, exc, status_code=status_code: _error(request, exc, status_code),
        )
