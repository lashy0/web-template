import base64
import binascii
import json
import os
from dataclasses import dataclass
from typing import Final, cast

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr, ValidationError

from .domain import ActivationType, LoRaWanVersion
from .exceptions import (
    CredentialsDecryptionError,
    CredentialsEncryptionConfigurationError,
    CredentialsPayloadError,
    UnsupportedCredentialsSchemaVersionError,
)
from .schemas import (
    Abp10Credentials,
    Abp11Credentials,
    Credentials,
    CredentialsPayload,
    Otaa10Credentials,
    Otaa11Credentials,
)

SCHEMA_VERSION_V1: Final = 1
NONCE_SIZE: Final = 12
_AES_256_KEY_SIZE: Final = 32
_AUTH_TAG_SIZE: Final = 16


@dataclass(frozen=True)
class CredentialsEncryptionContext:
    kg_dev_eui: str
    activation_type: ActivationType
    lorawan_version: LoRaWanVersion


def credentials_model_for_context(
    *,
    activation_type: ActivationType,
    lorawan_version: LoRaWanVersion,
    schema_version: int,
) -> type[CredentialsPayload]:
    if schema_version != SCHEMA_VERSION_V1:
        raise UnsupportedCredentialsSchemaVersionError

    models: dict[tuple[ActivationType, LoRaWanVersion], type[CredentialsPayload]] = {
        (ActivationType.OTAA, LoRaWanVersion.V1_0): Otaa10Credentials,
        (ActivationType.OTAA, LoRaWanVersion.V1_1): Otaa11Credentials,
        (ActivationType.ABP, LoRaWanVersion.V1_0): Abp10Credentials,
        (ActivationType.ABP, LoRaWanVersion.V1_1): Abp11Credentials,
    }

    try:
        return models[(activation_type, lorawan_version)]

    except KeyError as exc:
        raise CredentialsPayloadError from exc


def serialize_credentials_v1(
    credentials: Credentials,
    context: CredentialsEncryptionContext,
) -> bytes:
    """Return the canonical schema-v1 payload (sorted snake_case JSON)."""
    expected_model = credentials_model_for_context(
        activation_type=context.activation_type,
        lorawan_version=context.lorawan_version,
        schema_version=SCHEMA_VERSION_V1,
    )
    if type(credentials) is not expected_model:
        raise CredentialsPayloadError

    return json.dumps(
        credentials.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def decode_encryption_key(encoded_key: str | None) -> bytes:
    """Decode the configured URL-safe base64 AES-256 key without exposing it."""
    if not encoded_key:
        raise CredentialsEncryptionConfigurationError

    try:
        key = base64.b64decode(encoded_key.encode("ascii"), altchars=b"-_", validate=True)

    except (UnicodeEncodeError, binascii.Error):
        raise CredentialsEncryptionConfigurationError from None

    if len(key) != _AES_256_KEY_SIZE:
        raise CredentialsEncryptionConfigurationError

    return key


def resolve_encryption_key(secret: SecretStr | None) -> bytes:
    if not isinstance(secret, SecretStr):
        raise CredentialsEncryptionConfigurationError

    encoded_key = secret.get_secret_value()

    return decode_encryption_key(encoded_key)


class LoRaWanCredentialsCipher:
    """AES-256-GCM encryptor with a versioned payload and bound AAD."""

    def __init__(self, encryption_key: bytes | None) -> None:
        if not isinstance(encryption_key, bytes) or len(encryption_key) != _AES_256_KEY_SIZE:
            raise CredentialsEncryptionConfigurationError

        self._aesgcm = AESGCM(encryption_key)

    def encrypt_credentials(
        self,
        credentials: Credentials,
        context: CredentialsEncryptionContext,
    ) -> bytes:
        nonce = os.urandom(NONCE_SIZE)
        ciphertext_and_tag = self._aesgcm.encrypt(
            nonce,
            serialize_credentials_v1(credentials, context),
            _aad(context, SCHEMA_VERSION_V1),
        )

        return nonce + ciphertext_and_tag

    def decrypt_credentials(
        self,
        encrypted_data: bytes,
        schema_version: int,
        context: CredentialsEncryptionContext,
    ) -> Credentials:
        model = credentials_model_for_context(
            activation_type=context.activation_type,
            lorawan_version=context.lorawan_version,
            schema_version=schema_version,
        )
        if len(encrypted_data) < NONCE_SIZE + _AUTH_TAG_SIZE:
            raise CredentialsDecryptionError

        nonce = encrypted_data[:NONCE_SIZE]
        ciphertext_and_tag = encrypted_data[NONCE_SIZE:]

        try:
            payload = self._aesgcm.decrypt(
                nonce,
                ciphertext_and_tag,
                _aad(context, schema_version),
            )
            decoded_payload = json.loads(payload.decode("utf-8"))

            return cast(Credentials, model.model_validate(decoded_payload))

        except (InvalidTag, UnicodeDecodeError, json.JSONDecodeError, ValidationError):
            # Validation exceptions can include input values, which are credentials.
            raise CredentialsDecryptionError from None


def _aad(
    context: CredentialsEncryptionContext,
    schema_version: int,
) -> bytes:
    return json.dumps(
        {
            "activation_type": context.activation_type.value,
            "kg_dev_eui": context.kg_dev_eui,
            "lorawan_version": context.lorawan_version.value,
            "schema_version": schema_version,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
