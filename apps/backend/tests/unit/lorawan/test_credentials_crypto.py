import base64

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.modules.lorawan import ActivationType, LoRaWanVersion, generate_credentials
from app.modules.lorawan.crypto import (
    NONCE_SIZE,
    SCHEMA_VERSION_V1,
    CredentialsEncryptionContext,
    LoRaWanCredentialsCipher,
    _aad,
    serialize_credentials_v1,
)
from app.modules.lorawan.exceptions import (
    CredentialsDecryptionError,
    UnsupportedCredentialsSchemaVersionError,
)

_KEY = bytes(range(32))
_DEV_EUI = "0123456789abcdef"


def _context(
    activation_type: ActivationType,
    lorawan_version: LoRaWanVersion,
    *,
    dev_eui: str = _DEV_EUI,
) -> CredentialsEncryptionContext:
    return CredentialsEncryptionContext(
        kg_dev_eui=dev_eui,
        activation_type=activation_type,
        lorawan_version=lorawan_version,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("activation_type", "lorawan_version"),
    [
        (ActivationType.OTAA, LoRaWanVersion.V1_0),
        (ActivationType.OTAA, LoRaWanVersion.V1_1),
        (ActivationType.ABP, LoRaWanVersion.V1_0),
        (ActivationType.ABP, LoRaWanVersion.V1_1),
    ],
)
def test_generate_encrypt_decrypt_returns_the_original_typed_model(
    activation_type: ActivationType,
    lorawan_version: LoRaWanVersion,
) -> None:
    credentials = generate_credentials(_DEV_EUI, activation_type, lorawan_version)
    context = _context(activation_type, lorawan_version)

    encrypted = LoRaWanCredentialsCipher(_KEY).encrypt_credentials(credentials, context)
    restored = LoRaWanCredentialsCipher(_KEY).decrypt_credentials(
        encrypted, SCHEMA_VERSION_V1, context
    )

    assert type(restored) is type(credentials)
    assert restored == credentials


@pytest.mark.unit
def test_schema_v1_payload_is_canonical_compact_sorted_snake_case_json() -> None:
    context = _context(ActivationType.OTAA, LoRaWanVersion.V1_1)
    credentials = generate_credentials(_DEV_EUI, context.activation_type, context.lorawan_version)

    assert serialize_credentials_v1(credentials, context) == (
        b'{"app_key":"5feadae4a3a1a5e787c5da53b7a425da",'
        b'"dev_addr":"89abcdef","nwk_key":"a0b4766a61c39067c970d671988f0319"}'
    )


@pytest.mark.unit
def test_same_credentials_use_a_new_nonce_for_each_encryption() -> None:
    context = _context(ActivationType.ABP, LoRaWanVersion.V1_0)
    credentials = generate_credentials(_DEV_EUI, context.activation_type, context.lorawan_version)
    cipher = LoRaWanCredentialsCipher(_KEY)

    first = cipher.encrypt_credentials(credentials, context)
    second = cipher.encrypt_credentials(credentials, context)

    assert first != second
    assert first[:NONCE_SIZE] != second[:NONCE_SIZE]


@pytest.mark.unit
def test_ciphertext_tampering_is_detected() -> None:
    context = _context(ActivationType.ABP, LoRaWanVersion.V1_0)
    credentials = generate_credentials(_DEV_EUI, context.activation_type, context.lorawan_version)
    encrypted = bytearray(LoRaWanCredentialsCipher(_KEY).encrypt_credentials(credentials, context))
    encrypted[-1] ^= 1

    with pytest.raises(CredentialsDecryptionError):
        LoRaWanCredentialsCipher(_KEY).decrypt_credentials(
            bytes(encrypted), SCHEMA_VERSION_V1, context
        )


@pytest.mark.unit
def test_changed_dev_eui_or_lorawan_configuration_aad_is_detected() -> None:
    context = _context(ActivationType.OTAA, LoRaWanVersion.V1_0)
    credentials = generate_credentials(_DEV_EUI, context.activation_type, context.lorawan_version)
    encrypted = LoRaWanCredentialsCipher(_KEY).encrypt_credentials(credentials, context)

    changed_contexts = [
        _context(ActivationType.OTAA, LoRaWanVersion.V1_0, dev_eui="fedcba9876543210"),
        _context(ActivationType.OTAA, LoRaWanVersion.V1_1),
        _context(ActivationType.ABP, LoRaWanVersion.V1_0),
    ]
    for changed_context in changed_contexts:
        with pytest.raises(CredentialsDecryptionError):
            LoRaWanCredentialsCipher(_KEY).decrypt_credentials(
                encrypted, SCHEMA_VERSION_V1, changed_context
            )


@pytest.mark.unit
def test_incorrect_key_cannot_decrypt_credentials() -> None:
    context = _context(ActivationType.ABP, LoRaWanVersion.V1_1)
    credentials = generate_credentials(_DEV_EUI, context.activation_type, context.lorawan_version)
    encrypted = LoRaWanCredentialsCipher(_KEY).encrypt_credentials(credentials, context)

    with pytest.raises(CredentialsDecryptionError):
        LoRaWanCredentialsCipher(b"z" * 32).decrypt_credentials(
            encrypted, SCHEMA_VERSION_V1, context
        )


@pytest.mark.unit
def test_unknown_schema_version_is_rejected_before_decryption() -> None:
    context = _context(ActivationType.ABP, LoRaWanVersion.V1_1)
    credentials = generate_credentials(_DEV_EUI, context.activation_type, context.lorawan_version)
    encrypted = LoRaWanCredentialsCipher(_KEY).encrypt_credentials(credentials, context)

    with pytest.raises(UnsupportedCredentialsSchemaVersionError):
        LoRaWanCredentialsCipher(_KEY).decrypt_credentials(encrypted, 999, context)


@pytest.mark.unit
def test_validly_encrypted_payload_with_wrong_schema_is_rejected_safely() -> None:
    context = _context(ActivationType.OTAA, LoRaWanVersion.V1_0)
    nonce = b"n" * NONCE_SIZE
    encrypted = nonce + AESGCM(_KEY).encrypt(nonce, b"{}", _aad(context, SCHEMA_VERSION_V1))

    with pytest.raises(CredentialsDecryptionError) as error:
        LoRaWanCredentialsCipher(_KEY).decrypt_credentials(encrypted, SCHEMA_VERSION_V1, context)

    assert "{}" not in str(error.value)


@pytest.mark.unit
def test_configured_key_encoding_is_urlsafe_base64() -> None:
    encoded = base64.urlsafe_b64encode(_KEY).decode("ascii")

    from app.modules.lorawan.crypto import decode_encryption_key

    assert decode_encryption_key(encoded) == _KEY
