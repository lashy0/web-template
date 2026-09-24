"""Errors raised while communicating with Hydra."""

from app.lib.exceptions import (
    ApplicationConflictError,
    ApplicationError,
    ApplicationNotFoundError,
    ServiceUnavailableError,
)


class HydraError(ApplicationError):
    """Base Hydra integration error."""


class HydraUnavailableError(HydraError, ServiceUnavailableError):
    """Hydra is unavailable or returned an unexpected response."""


class HydraClientNotFoundError(ApplicationNotFoundError):
    """The requested OAuth client does not exist in Hydra."""


class HydraClientAlreadyExistsError(ApplicationConflictError):
    """An OAuth client with the same ID already exists in Hydra."""
