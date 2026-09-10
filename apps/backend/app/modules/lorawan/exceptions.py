from app.core.exceptions import AppError, InvalidInputError


class CredentialsGenerationError(InvalidInputError):
    """Base error for invalid credential-generator input."""


class InvalidDevEuiError(CredentialsGenerationError):
    """Raised when a DevEUI is not exactly eight bytes encoded as hex."""


class LoRaWanCredentialsError(AppError):
    """Base class for safe persisted-credentials failures."""


class CredentialsEncryptionConfigurationError(LoRaWanCredentialsError, InvalidInputError):
    code = "lorawan_credentials_encryption_configuration_error"

    default_message = "LoRaWAN credentials encryption is not configured correctly"


class CredentialsDecryptionError(LoRaWanCredentialsError):
    code = "lorawan_credentials_decryption_error"

    default_message = "Stored LoRaWAN credentials cannot be decrypted"


class CredentialsPayloadError(LoRaWanCredentialsError, InvalidInputError):
    code = "lorawan_credentials_payload_error"

    default_message = "LoRaWAN credentials payload is invalid"


class UnsupportedCredentialsSchemaVersionError(LoRaWanCredentialsError, InvalidInputError):
    code = "lorawan_credentials_schema_version_unsupported"

    default_message = "LoRaWAN credentials schema version is unsupported"
