"""Authenticated encryption for persisted PAK OAuth client secrets."""

from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr

from app.lib.exceptions import ApplicationError


class PakAccessKeyConfigurationError(ApplicationError):
    """The PAK access-key encryption configuration or ciphertext is invalid."""


class PakAccessKeyCipher:
    """Encrypt and decrypt PAK OAuth client secrets with Fernet."""

    def __init__(self, key: SecretStr | str | None) -> None:
        if isinstance(key, SecretStr):
            key = key.get_secret_value()

        if not key:
            raise PakAccessKeyConfigurationError(
                detail="BACKEND_PAK_ACCESS_KEY_ENCRYPTION_KEY is required for PAK access keys."
            )

        try:
            self._fernet = Fernet(key.encode("ascii"))
        except (UnicodeEncodeError, ValueError) as exc:
            raise PakAccessKeyConfigurationError(
                detail="BACKEND_PAK_ACCESS_KEY_ENCRYPTION_KEY must be a valid Fernet key."
            ) from exc

    def encrypt(self, access_key: str) -> str:
        """Encrypt a plaintext OAuth client secret for persistence."""
        return self._fernet.encrypt(access_key.encode("utf-8")).decode("ascii")

    def decrypt(self, encrypted_access_key: str) -> str:
        """Decrypt a persisted OAuth client secret."""
        try:
            return self._fernet.decrypt(encrypted_access_key.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError) as exc:
            raise PakAccessKeyConfigurationError(detail="Stored PAK access key cannot be decrypted.") from exc
