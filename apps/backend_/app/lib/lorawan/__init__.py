"""LoRaWAN DevEUI allocation, credential generation and credential encryption.

Pure functions without database or configuration access; the production domain
supplies keys, locks and persistence.
"""

from app.lib.lorawan.crypto import (
    SCHEMA_VERSION_V1,
    CredentialsEncryptionContext,
    LoRaWanCredentialsCipher,
    decode_encryption_key,
)
from app.lib.lorawan.dev_eui import (
    derive_dev_eui_range,
    normalize_dev_eui,
    normalize_dev_eui_prefix,
)
from app.lib.lorawan.exceptions import (
    CredentialsDecryptionError,
    CredentialsEncryptionConfigurationError,
    CredentialsError,
    CredentialsPayloadError,
    DevEuiRangeOverflowError,
    InvalidDevEuiError,
    InvalidDevEuiPrefixError,
    UnsupportedCredentialsSchemaVersionError,
)
from app.lib.lorawan.generator import generate_credentials
from app.lib.lorawan.schemas import (
    Abp10Credentials,
    Abp11Credentials,
    ActivationType,
    Credentials,
    CredentialsPayload,
    LoRaWanVersion,
    Otaa10Credentials,
    Otaa11Credentials,
)

__all__ = (
    "SCHEMA_VERSION_V1",
    "Abp10Credentials",
    "Abp11Credentials",
    "ActivationType",
    "Credentials",
    "CredentialsDecryptionError",
    "CredentialsEncryptionConfigurationError",
    "CredentialsEncryptionContext",
    "CredentialsError",
    "CredentialsPayload",
    "CredentialsPayloadError",
    "DevEuiRangeOverflowError",
    "InvalidDevEuiError",
    "InvalidDevEuiPrefixError",
    "LoRaWanCredentialsCipher",
    "LoRaWanVersion",
    "Otaa10Credentials",
    "Otaa11Credentials",
    "UnsupportedCredentialsSchemaVersionError",
    "decode_encryption_key",
    "derive_dev_eui_range",
    "generate_credentials",
    "normalize_dev_eui",
    "normalize_dev_eui_prefix",
)
