"""Narrow production-internal persistence boundary for preparation credentials."""

from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.keygen.crypto import (
    SCHEMA_VERSION_V1,
    CredentialsEncryptionContext,
    LoRaWanCredentialsCipher,
    resolve_encryption_key,
)
from app.components.keygen.types import Credentials
from app.contexts.production.batches.model import Batch
from app.modules.kg.exceptions import KgLoRaWanCredentialsAlreadyExistError
from app.modules.kg.models import LoRaWanCredentials


class PreparationCredentials:
    """Write encrypted credentials without depending on the legacy KG service facade."""

    def __init__(self, session: AsyncSession, encryption_key: SecretStr | None) -> None:
        self._session = session
        self._cipher = LoRaWanCredentialsCipher(resolve_encryption_key(encryption_key))

    async def save(
        self, *, batch: Batch, kg_dev_eui: str, credentials: Credentials
    ) -> None:
        config = batch.lorawan_config
        if config is None:
            raise RuntimeError("Batch does not have a LoRaWAN configuration")
        encrypted_data = self._cipher.encrypt_credentials(
            credentials,
            CredentialsEncryptionContext(
                kg_dev_eui=kg_dev_eui,
                activation_type=config.activation_type,
                lorawan_version=config.lorawan_version,
            ),
        )
        try:
            async with self._session.begin_nested():
                self._session.add(
                    LoRaWanCredentials(
                        kg_dev_eui=kg_dev_eui,
                        schema_version=SCHEMA_VERSION_V1,
                        encrypted_data=encrypted_data,
                    )
                )
                await self._session.flush()
        except IntegrityError as exc:
            raise KgLoRaWanCredentialsAlreadyExistError from exc
