"""Deprecated compatibility bridge; use :mod:`app.components.keygen.exceptions`."""

from app.components.keygen.exceptions import (
    CredentialsDecryptionError,
    CredentialsEncryptionConfigurationError,
    CredentialsGenerationError,
    CredentialsPayloadError,
    InvalidDevEuiError,
    LoRaWanCredentialsError,
    UnsupportedCredentialsSchemaVersionError,
)

__all__ = [
    "CredentialsDecryptionError",
    "CredentialsEncryptionConfigurationError",
    "CredentialsGenerationError",
    "CredentialsPayloadError",
    "InvalidDevEuiError",
    "LoRaWanCredentialsError",
    "UnsupportedCredentialsSchemaVersionError",
]
