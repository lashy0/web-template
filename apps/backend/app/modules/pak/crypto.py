from cryptography.fernet import Fernet, InvalidToken

from .exceptions import PakAccessKeyConfigurationError


class PakAccessKeyCipher:
    """Authenticated encryption for persisted PAK OAuth client secrets."""

    def __init__(self, key: str | None) -> None:
        if not key:
            raise PakAccessKeyConfigurationError(
                "BACKEND_PAK_ACCESS_KEY_ENCRYPTION_KEY is required for PAK access keys"
            )

        try:
            self._fernet = Fernet(key.encode("ascii"))

        except (UnicodeEncodeError, ValueError) as exc:
            raise PakAccessKeyConfigurationError(
                "BACKEND_PAK_ACCESS_KEY_ENCRYPTION_KEY must be a valid Fernet key"
            ) from exc

    def encrypt(self, access_key: str) -> str:
        return self._fernet.encrypt(access_key.encode("utf-8")).decode("ascii")

    def decrypt(self, encrypted_access_key: str) -> str:
        try:
            return self._fernet.decrypt(encrypted_access_key.encode("ascii")).decode("utf-8")

        except (InvalidToken, UnicodeDecodeError) as exc:
            raise PakAccessKeyConfigurationError(
                "Stored PAK access key cannot be decrypted"
            ) from exc
