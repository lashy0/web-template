from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.auth.exceptions import (
    AccountDisabledError,
    ForbiddenError,
    IdentityAlreadyExistsError,
    IdentityNotFoundError,
    IdentityProviderUnavailableError,
    InvalidSessionError,
    UserNotProvisionedError,
    UserProvisioningError,
)


def _error(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", ""),
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    mappings: list[tuple[type[Exception], str, int]] = [
        (InvalidSessionError, "invalid_session", status.HTTP_401_UNAUTHORIZED),
        (AccountDisabledError, "account_disabled", status.HTTP_403_FORBIDDEN),
        (UserNotProvisionedError, "user_not_provisioned", status.HTTP_403_FORBIDDEN),
        (ForbiddenError, "forbidden", status.HTTP_403_FORBIDDEN),
        (IdentityAlreadyExistsError, "login_already_exists", status.HTTP_409_CONFLICT),
        (
            UserProvisioningError,
            "user_provisioning_failed",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ),
        (IdentityNotFoundError, "user_not_found", status.HTTP_404_NOT_FOUND),
        (
            IdentityProviderUnavailableError,
            "identity_provider_unavailable",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ),
    ]
    for exception, code, status_code in mappings:
        app.add_exception_handler(
            exception,
            lambda request, exc, code=code, status_code=status_code: _error(
                request, code, str(exc) or code.replace("_", " "), status_code
            ),
        )
