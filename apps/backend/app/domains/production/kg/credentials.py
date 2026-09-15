"""Credential persistence application API owned by production KG."""

from uuid import UUID

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
from app.domains.production.batches.model import Batch

from .exceptions import (
    KgLoRaWanConfigurationMissingError,
    KgLoRaWanCredentialsAlreadyExistError,
    KgLoRaWanCredentialsNotFoundError,
    KgNotFoundError,
)
from .model import LoRaWanCredentials
from .repository import KgRepository


class KgCredentials:
    """Small caller-owned-UoW API; it is deliberately not a service facade."""

    def __init__(self, session: AsyncSession, encryption_key: SecretStr | None) -> None:
        self._session = session
        self._repository = KgRepository(session)
        self._cipher = LoRaWanCredentialsCipher(resolve_encryption_key(encryption_key))

    async def save(self, *, batch: Batch, kg_dev_eui: str, credentials: Credentials) -> None:
        config = batch.lorawan_config
        if config is None:
            raise KgLoRaWanConfigurationMissingError
        encrypted_data = self._cipher.encrypt_credentials(
            credentials,
            CredentialsEncryptionContext(
                kg_dev_eui=kg_dev_eui,
                activation_type=config.activation_type,
                lorawan_version=config.lorawan_version,
            ),
        )
        if await self._repository.credentials_exist(kg_dev_eui):
            raise KgLoRaWanCredentialsAlreadyExistError
        try:
            async with self._session.begin_nested():
                await self._repository.save_credentials(
                    LoRaWanCredentials(
                        kg_dev_eui=kg_dev_eui,
                        schema_version=SCHEMA_VERSION_V1,
                        encrypted_data=encrypted_data,
                    )
                )
        except IntegrityError as exc:
            # Keep a duplicate race idempotent while exposing other DB failures.
            raise KgLoRaWanCredentialsAlreadyExistError from exc

    async def exists(self, *, kg_dev_eui: str) -> bool:
        return await self._repository.credentials_exist(kg_dev_eui)

    async def save_credentials(self, *, kg_dev_eui: str, credentials: Credentials) -> None:
        """Compatibility spelling for callers still entering through the old API."""
        kg = await self._repository.get_by_dev_eui(kg_dev_eui)
        if kg is None:
            raise KgNotFoundError
        await self.save(batch=kg.batch, kg_dev_eui=kg_dev_eui, credentials=credentials)

    async def credentials_exist(self, *, kg_dev_eui: str) -> bool:
        return await self.exists(kg_dev_eui=kg_dev_eui)

    async def count_for_batch(self, batch_id: UUID) -> int:
        return await self._repository.count_credentials_for_batch(batch_id)

    async def load(self, *, kg_dev_eui: str) -> Credentials:
        kg = await self._repository.get_by_dev_eui(kg_dev_eui)
        if kg is None:
            raise KgNotFoundError
        if kg.batch.lorawan_config is None:
            raise KgLoRaWanConfigurationMissingError
        stored = await self._repository.get_credentials(kg_dev_eui)
        if stored is None:
            raise KgLoRaWanCredentialsNotFoundError
        return self._cipher.decrypt_credentials(
            stored.encrypted_data,
            stored.schema_version,
            CredentialsEncryptionContext(
                kg_dev_eui=kg.dev_eui,
                activation_type=kg.batch.lorawan_config.activation_type,
                lorawan_version=kg.batch.lorawan_config.lorawan_version,
            ),
        )

    async def load_credentials(self, *, kg_dev_eui: str) -> Credentials:
        return await self.load(kg_dev_eui=kg_dev_eui)
