from typing import Any, ClassVar


class AppError(Exception):
    """Base class for expected application errors."""

    code: ClassVar[str] = "application_error"
    default_message: ClassVar[str] = "application error"

    def __init__(
        self,
        message: str | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details

        super().__init__(self.message)


class NotFoundError(AppError):
    """The requested resource does not exist."""


class ConflictError(AppError):
    """The operation conflicts with current application state."""


class PermissionDeniedError(AppError):
    """The actor is not allowed to perform the operation."""


class UnauthenticatedError(AppError):
    """Valid authentication is required."""


class DependencyUnavailableError(AppError):
    """A required external dependency cannot complete the operation."""
