"""Deprecated compatibility bridge; use :mod:`app.components.keygen.crypto`."""

from app.components.keygen.crypto import (
    NONCE_SIZE,
    SCHEMA_VERSION_V1,
    CredentialsEncryptionContext,
    LoRaWanCredentialsCipher,
    _aad,
    credentials_model_for_context,
    decode_encryption_key,
    resolve_encryption_key,
    serialize_credentials_v1,
)

__all__ = [
    "NONCE_SIZE",
    "SCHEMA_VERSION_V1",
    "CredentialsEncryptionContext",
    "LoRaWanCredentialsCipher",
    "_aad",
    "credentials_model_for_context",
    "decode_encryption_key",
    "resolve_encryption_key",
    "serialize_credentials_v1",
]
