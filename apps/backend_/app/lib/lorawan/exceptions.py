"""LoRaWAN DevEUI and credential errors."""

from app.lib.exceptions import (
    ApplicationClientError,
    ApplicationConflictError,
    ApplicationError,
)


class InvalidDevEuiError(ApplicationClientError):
    """A DevEUI is not exactly eight bytes encoded as hex (HTTP 400)."""

    code = "invalid_dev_eui"
    detail = "DevEUI must contain exactly 16 hexadecimal characters."


class InvalidDevEuiPrefixError(ApplicationClientError):
    """A DevEUI prefix is not exactly five bytes encoded as hex (HTTP 400)."""

    code = "invalid_dev_eui_prefix"
    detail = "DevEUI prefix must contain exactly 10 hexadecimal characters."


class DevEuiRangeOverflowError(ApplicationConflictError):
    """The prefix has no room left for the requested DevEUI range (HTTP 409)."""

    code = "dev_eui_range_overflow"
    detail = "The DevEUI prefix has no room for the requested quantity."


class CredentialsError(ApplicationError):
    """Stored credentials or their configuration are unusable (HTTP 500).

    These are server faults: the client cannot fix them, and details must not
    reveal key material or plaintext.
    """


class CredentialsEncryptionConfigurationError(CredentialsError):
    """The credentials encryption key is missing or invalid."""

    detail = "LoRaWAN credentials encryption is not configured correctly."


class CredentialsPayloadError(CredentialsError):
    """Credentials do not match the payload type of their LoRaWAN configuration."""

    detail = "LoRaWAN credentials payload is invalid."


class UnsupportedCredentialsSchemaVersionError(CredentialsError):
    """Stored credentials use an unknown schema version."""

    detail = "LoRaWAN credentials schema version is unsupported."


class CredentialsDecryptionError(CredentialsError):
    """Stored credentials cannot be authenticated or decoded."""

    detail = "Stored LoRaWAN credentials cannot be decrypted."


__all__ = (
    "CredentialsDecryptionError",
    "CredentialsEncryptionConfigurationError",
    "CredentialsError",
    "CredentialsPayloadError",
    "DevEuiRangeOverflowError",
    "InvalidDevEuiError",
    "InvalidDevEuiPrefixError",
    "UnsupportedCredentialsSchemaVersionError",
)
