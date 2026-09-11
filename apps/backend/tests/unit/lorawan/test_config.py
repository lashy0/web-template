import base64

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.lorawan.crypto import resolve_encryption_key
from app.modules.lorawan.exceptions import CredentialsEncryptionConfigurationError

_VALID_KEY = bytes(range(32))


@pytest.mark.unit
def test_lorawan_credentials_key_is_required_when_crypto_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BACKEND_LORAWAN_CREDENTIALS_ENCRYPTION_KEY", raising=False)
    settings = Settings()

    assert settings.LORAWAN_CREDENTIALS_ENCRYPTION_KEY is None
    with pytest.raises(CredentialsEncryptionConfigurationError):
        resolve_encryption_key(settings.LORAWAN_CREDENTIALS_ENCRYPTION_KEY)


@pytest.mark.unit
@pytest.mark.parametrize(
    "encoded_key",
    [
        pytest.param("not a base64 key!", id="invalid-base64"),
        pytest.param(
            base64.urlsafe_b64encode(b"too-short").decode("ascii"),
            id="wrong-length",
        ),
    ],
)
def test_lorawan_credentials_key_rejects_invalid_configuration_safely(
    encoded_key: str,
) -> None:
    with pytest.raises(CredentialsEncryptionConfigurationError) as error:
        resolve_encryption_key(SecretStr(encoded_key))

    assert encoded_key not in str(error.value)


@pytest.mark.unit
def test_lorawan_credentials_key_returns_valid_aes_256_key() -> None:
    encoded_key = base64.urlsafe_b64encode(_VALID_KEY).decode("ascii")
    assert resolve_encryption_key(SecretStr(encoded_key)) == _VALID_KEY


@pytest.mark.unit
def test_cipher_rejects_missing_key_for_direct_callers() -> None:
    from app.modules.lorawan.crypto import LoRaWanCredentialsCipher

    with pytest.raises(CredentialsEncryptionConfigurationError):
        LoRaWanCredentialsCipher(None)
