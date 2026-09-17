from app.lib.exceptions import ApplicationClientError, ApplicationError


class KratosError(ApplicationError):
    """Base Kratos integration error."""


class KratosUnavailableError(KratosError):
    """Kratos is unavailable or returned an unexpected response."""


class KratosIdentityNotFoundError(ApplicationClientError):
    """Kratos identity was not found."""


class KratosIdentityAlreadyExistsError(ApplicationClientError):
    """Kratos identity already exists."""


class KratosInvalidSessionError(ApplicationClientError):
    """Kratos session is invalid."""
