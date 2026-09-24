from app.lib.exceptions import (
    ApplicationClientError,
    ApplicationConflictError,
    ApplicationError,
    ApplicationNotFoundError,
    ServiceUnavailableError,
)


class KratosError(ApplicationError):
    """Base Kratos integration error."""


class KratosUnavailableError(KratosError, ServiceUnavailableError):
    """Kratos is unavailable or returned an unexpected response."""


class KratosIdentityNotFoundError(ApplicationNotFoundError):
    """Kratos identity was not found."""


class KratosIdentityAlreadyExistsError(ApplicationConflictError):
    """Kratos identity already exists."""


class KratosInvalidSessionError(ApplicationClientError):
    """Kratos session is invalid."""
