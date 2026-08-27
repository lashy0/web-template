import pytest
from cryptography.fernet import Fernet

from app.modules.pak.crypto import PakAccessKeyCipher
from app.modules.pak.exceptions import PakAccessKeyConfigurationError


@pytest.mark.unit
def test_access_key_is_encrypted_and_round_trips() -> None:
    cipher = PakAccessKeyCipher(Fernet.generate_key().decode("ascii"))

    encrypted = cipher.encrypt("client-secret")

    assert encrypted != "client-secret"
    assert cipher.decrypt(encrypted) == "client-secret"


@pytest.mark.unit
def test_access_key_cipher_rejects_missing_key() -> None:
    with pytest.raises(PakAccessKeyConfigurationError):
        PakAccessKeyCipher(None)
