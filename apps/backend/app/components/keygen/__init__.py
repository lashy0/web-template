"""Pure LoRaWAN credential generation and credential-envelope primitives."""

from .crypto import (
    NONCE_SIZE,
    SCHEMA_VERSION_V1,
    CredentialsEncryptionContext,
    LoRaWanCredentialsCipher,
    decode_encryption_key,
    resolve_encryption_key,
    serialize_credentials_v1,
)
from .dev_eui import (
    derive_dev_eui_range,
    normalize_dev_eui,
    normalize_dev_eui_prefix,
)
from .exceptions import (
    CredentialsDecryptionError,
    CredentialsEncryptionConfigurationError,
    CredentialsGenerationError,
    CredentialsPayloadError,
    DevEuiRangeOverflowError,
    InvalidDevEuiError,
    InvalidDevEuiPrefixError,
    UnsupportedCredentialsSchemaVersionError,
)
from .generator import generate_credentials
from .types import (
    Abp10Credentials,
    Abp11Credentials,
    ActivationType,
    Credentials,
    CredentialsPayload,
    LoRaWanVersion,
    Otaa10Credentials,
    Otaa11Credentials,
)

__all__ = [
    "Abp10Credentials",
    "Abp11Credentials",
    "ActivationType",
    "Credentials",
    "CredentialsDecryptionError",
    "CredentialsEncryptionConfigurationError",
    "CredentialsEncryptionContext",
    "CredentialsGenerationError",
    "CredentialsPayload",
    "CredentialsPayloadError",
    "DevEuiRangeOverflowError",
    "InvalidDevEuiError",
    "InvalidDevEuiPrefixError",
    "LoRaWanCredentialsCipher",
    "LoRaWanVersion",
    "NONCE_SIZE",
    "Otaa10Credentials",
    "Otaa11Credentials",
    "SCHEMA_VERSION_V1",
    "UnsupportedCredentialsSchemaVersionError",
    "decode_encryption_key",
    "derive_dev_eui_range",
    "generate_credentials",
    "normalize_dev_eui",
    "normalize_dev_eui_prefix",
    "resolve_encryption_key",
    "serialize_credentials_v1",
]
