from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.exceptions import (
    AppError,
    ConflictError,
    DependencyUnavailableError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
)

ERROR_STATUS_CODES: dict[type[AppError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    UnauthenticatedError: status.HTTP_401_UNAUTHORIZED,
    DependencyUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


async def application_error_handler(request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, AppError):
        raise error

    request_id = getattr(request.state, "request_id", "")
    status_code = next(
        (
            error_status_code
            for error_type, error_status_code in ERROR_STATUS_CODES.items()
            if isinstance(error, error_type)
        ),
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    if status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.bind(request_id=request_id, error_type=type(error).__name__).opt(
            exception=error
        ).error("Unclassified application error")
        code, message = "application_error", "Internal server error"

    else:
        code, message = error.code, str(error) or error.code.replace("_", " ")

    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "request_id": request_id,
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, application_error_handler)
