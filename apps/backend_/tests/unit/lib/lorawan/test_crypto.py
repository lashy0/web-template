import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr

from app.lib.lorawan import (
    SCHEMA_VERSION_V1,
    ActivationType,
    CredentialsDecryptionError,
    CredentialsEncryptionConfigurationError,
    CredentialsEncryptionContext,
    CredentialsPayloadError,
    LoRaWanCredentialsCipher,
    LoRaWanVersion,
    Otaa10Credentials,
    Otaa11Credentials,
    UnsupportedCredentialsSchemaVersionError,
    decode_encryption_key,
)

pytestmark = pytest.mark.unit

_KEY = bytes(range(32))
_OTAA_1_1 = CredentialsEncryptionContext("0123456789abcdef", ActivationType.OTAA, LoRaWanVersion.V1_1)
_OTAA_1_1_CREDENTIALS = Otaa11Credentials(
    dev_addr="89abcdef",
    app_key="5feadae4a3a1a5e787c5da53b7a425da",
    nwk_key="a0b4766a61c39067c970d671988f0319",
)

# ``_OTAA_1_1_CREDENTIALS`` encrypted by the legacy backend with ``_KEY``. Stored
# ciphertexts depend on its payload layout and associated data, so reading it is
# the compatibility contract. Layout: nonce || encrypted payload || GCM tag.
_LEGACY_NONCE = bytes(range(12))
_LEGACY_ENCRYPTED_PAYLOAD = bytes.fromhex(  # 113 bytes, as long as the JSON payload
    "3c20b76b b5baa97e f463ada9 848f1d0c e7b7e200 91483e4d"
    "595280b2 255e6387 65719bcf cdf673ac 46911b8c aaab0a5c"
    "8b2f3fec 3eb2d1f8 05b51220 7981968a 955ae456 f1bf510a"
    "433fcf17 cdb52c89 08e8fd55 4055325e cc9eadf5 48c68eee"
    "f2cf6982 9276f923 a6245882 7b44185d c7"
)
_LEGACY_TAG = bytes.fromhex("b8c8a27b 6b4ac25b bc2ae6e8 343862db")
_LEGACY_CIPHERTEXT = _LEGACY_NONCE + _LEGACY_ENCRYPTED_PAYLOAD + _LEGACY_TAG


def test_decrypt_reads_legacy_ciphertext() -> None:
    credentials = LoRaWanCredentialsCipher(_KEY).decrypt(_LEGACY_CIPHERTEXT, SCHEMA_VERSION_V1, _OTAA_1_1)

    assert credentials == _OTAA_1_1_CREDENTIALS


def test_encrypt_output_decrypts_to_same_credentials() -> None:
    cipher = LoRaWanCredentialsCipher(_KEY)

    encrypted = cipher.encrypt(_OTAA_1_1_CREDENTIALS, _OTAA_1_1)

    assert cipher.decrypt(encrypted, SCHEMA_VERSION_V1, _OTAA_1_1) == _OTAA_1_1_CREDENTIALS


def test_encrypt_same_credentials_twice_differs() -> None:
    cipher = LoRaWanCredentialsCipher(_KEY)

    first = cipher.encrypt(_OTAA_1_1_CREDENTIALS, _OTAA_1_1)
    second = cipher.encrypt(_OTAA_1_1_CREDENTIALS, _OTAA_1_1)

    assert first != second


def test_encrypt_rejects_credentials_of_other_configuration() -> None:
    credentials = Otaa10Credentials(dev_addr="89abcdef", app_key="5feadae4a3a1a5e787c5da53b7a425da")

    with pytest.raises(CredentialsPayloadError):
        LoRaWanCredentialsCipher(_KEY).encrypt(credentials, _OTAA_1_1)


def test_decrypt_rejects_ciphertext_of_other_device() -> None:
    other_device = CredentialsEncryptionContext("fedcba9876543210", ActivationType.OTAA, LoRaWanVersion.V1_1)

    with pytest.raises(CredentialsDecryptionError):
        LoRaWanCredentialsCipher(_KEY).decrypt(_LEGACY_CIPHERTEXT, SCHEMA_VERSION_V1, other_device)


def test_decrypt_rejects_ciphertext_shorter_than_nonce_and_tag() -> None:
    truncated = _LEGACY_NONCE + _LEGACY_TAG[:-1]

    with pytest.raises(CredentialsDecryptionError):
        LoRaWanCredentialsCipher(_KEY).decrypt(truncated, SCHEMA_VERSION_V1, _OTAA_1_1)


def test_decrypt_rejects_unknown_schema_version() -> None:
    with pytest.raises(UnsupportedCredentialsSchemaVersionError):
        LoRaWanCredentialsCipher(_KEY).decrypt(_LEGACY_CIPHERTEXT, SCHEMA_VERSION_V1 + 1, _OTAA_1_1)


def test_decrypt_rejects_authentic_payload_of_wrong_shape_without_revealing_it() -> None:
    nonce = bytes(12)
    associated_data = (
        b'{"activation_type":"otaa","kg_dev_eui":"0123456789abcdef","lorawan_version":"1.1","schema_version":1}'
    )
    encrypted = nonce + AESGCM(_KEY).encrypt(nonce, b'{"secret":"plaintext"}', associated_data)

    with pytest.raises(CredentialsDecryptionError) as error:
        LoRaWanCredentialsCipher(_KEY).decrypt(encrypted, SCHEMA_VERSION_V1, _OTAA_1_1)

    assert "plaintext" not in repr(error.value)


def test_cipher_rejects_key_of_wrong_length() -> None:
    with pytest.raises(CredentialsEncryptionConfigurationError):
        LoRaWanCredentialsCipher(bytes(16))


def test_decode_encryption_key_reads_urlsafe_base64() -> None:
    key = decode_encryption_key(SecretStr("-_v7-_v7-_v7-_v7-_v7-_v7-_v7-_v7-_v7-_v7-_s="))

    assert key == bytes([0xFB] * 32)


@pytest.mark.parametrize(
    "secret",
    [None, "not a base64 key!", "dG9vLXNob3J0"],
    ids=["missing", "not-base64", "wrong-length"],
)
def test_decode_encryption_key_rejects_invalid_key(secret: str | None) -> None:
    with pytest.raises(CredentialsEncryptionConfigurationError):
        decode_encryption_key(secret)
