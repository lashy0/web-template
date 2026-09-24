"""AES-256-GCM encryption of persisted LoRaWAN credentials.

The ciphertext is ``nonce || ciphertext || tag``. The DevEUI, the LoRaWAN
configuration and the schema version are bound as associated data, so a
ciphertext copied to another device or configuration fails to decrypt.
"""

import base64
import binascii
import json
import os
from dataclasses import dataclass
from typing import Final

import msgspec
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr

from app.lib.lorawan.exceptions import (
    CredentialsDecryptionError,
    CredentialsEncryptionConfigurationError,
    CredentialsPayloadError,
    UnsupportedCredentialsSchemaVersionError,
)
from app.lib.lorawan.schemas import (
    Abp10Credentials,
    Abp11Credentials,
    ActivationType,
    Credentials,
    LoRaWanVersion,
    Otaa10Credentials,
    Otaa11Credentials,
)

SCHEMA_VERSION_V1: Final = 1
_NONCE_SIZE: Final = 12
_AES_256_KEY_SIZE: Final = 32
_AUTH_TAG_SIZE: Final = 16

_PAYLOAD_TYPES: Final[dict[tuple[ActivationType, LoRaWanVersion], type[Credentials]]] = {
    (ActivationType.OTAA, LoRaWanVersion.V1_0): Otaa10Credentials,
    (ActivationType.OTAA, LoRaWanVersion.V1_1): Otaa11Credentials,
    (ActivationType.ABP, LoRaWanVersion.V1_0): Abp10Credentials,
    (ActivationType.ABP, LoRaWanVersion.V1_1): Abp11Credentials,
}


@dataclass(frozen=True, slots=True)
class CredentialsEncryptionContext:
    """What a ciphertext is bound to."""

    dev_eui: str
    activation_type: ActivationType
    lorawan_version: LoRaWanVersion


def decode_encryption_key(secret: SecretStr | str | None) -> bytes:
    """Decode the configured URL-safe base64 AES-256 key without exposing it.

    Raises:
        CredentialsEncryptionConfigurationError: The key is missing, not base64
            or not 32 bytes long.
    """
    if isinstance(secret, SecretStr):
        secret = secret.get_secret_value()

    if not secret:
        raise CredentialsEncryptionConfigurationError

    try:
        key = base64.b64decode(secret.encode("ascii"), altchars=b"-_", validate=True)
    except (UnicodeEncodeError, binascii.Error):
        raise CredentialsEncryptionConfigurationError from None

    if len(key) != _AES_256_KEY_SIZE:
        raise CredentialsEncryptionConfigurationError

    return key


class LoRaWanCredentialsCipher:
    """Encrypt and decrypt credentials with a versioned payload and bound context."""

    __slots__ = ("_aesgcm",)

    def __init__(self, key: bytes) -> None:
        if len(key) != _AES_256_KEY_SIZE:
            raise CredentialsEncryptionConfigurationError

        self._aesgcm = AESGCM(key)

    def encrypt(self, credentials: Credentials, context: CredentialsEncryptionContext) -> bytes:
        """Encrypt credentials with a fresh nonce.

        Raises:
            CredentialsPayloadError: The payload type does not match the context.
        """
        nonce = os.urandom(_NONCE_SIZE)
        payload = _serialize_credentials_v1(credentials, context)

        return nonce + self._aesgcm.encrypt(nonce, payload, _associated_data(context, SCHEMA_VERSION_V1))

    def decrypt(
        self,
        encrypted: bytes,
        schema_version: int,
        context: CredentialsEncryptionContext,
    ) -> Credentials:
        """Authenticate and decode stored credentials.

        Raises:
            UnsupportedCredentialsSchemaVersionError: Unknown ``schema_version``.
            CredentialsDecryptionError: Wrong key, tampered data or another context.
        """
        payload_type = _payload_type(context, schema_version)

        if len(encrypted) < _NONCE_SIZE + _AUTH_TAG_SIZE:
            raise CredentialsDecryptionError

        nonce, ciphertext = encrypted[:_NONCE_SIZE], encrypted[_NONCE_SIZE:]

        try:
            payload = self._aesgcm.decrypt(nonce, ciphertext, _associated_data(context, schema_version))

            return msgspec.json.decode(payload, type=payload_type)
        except (InvalidTag, msgspec.DecodeError):
            # Deliberately without a cause: it may carry plaintext fragments.
            raise CredentialsDecryptionError from None


def _serialize_credentials_v1(
    credentials: Credentials,
    context: CredentialsEncryptionContext,
) -> bytes:
    """Return the canonical schema-v1 payload: compact JSON with sorted keys.

    Raises:
        CredentialsPayloadError: The payload type does not match the context.
    """
    if type(credentials) is not _payload_type(context, SCHEMA_VERSION_V1):
        raise CredentialsPayloadError

    return msgspec.json.encode(credentials, order="sorted")


def _payload_type(context: CredentialsEncryptionContext, schema_version: int) -> type[Credentials]:
    if schema_version != SCHEMA_VERSION_V1:
        raise UnsupportedCredentialsSchemaVersionError

    return _PAYLOAD_TYPES[(context.activation_type, context.lorawan_version)]


def _associated_data(context: CredentialsEncryptionContext, schema_version: int) -> bytes:
    return json.dumps(
        {
            "activation_type": context.activation_type.value,
            "kg_dev_eui": context.dev_eui,
            "lorawan_version": context.lorawan_version.value,
            "schema_version": schema_version,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


__all__ = (
    "SCHEMA_VERSION_V1",
    "CredentialsEncryptionContext",
    "LoRaWanCredentialsCipher",
    "decode_encryption_key",
)
