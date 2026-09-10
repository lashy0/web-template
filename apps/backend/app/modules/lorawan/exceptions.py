from app.core.exceptions import InvalidInputError


class CredentialsGenerationError(InvalidInputError):
    """Base error for invalid credential-generator input."""


class InvalidDevEuiError(CredentialsGenerationError):
    """Raised when a DevEUI is not exactly eight bytes encoded as hex."""
