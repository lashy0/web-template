from __future__ import annotations

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.batch.models import Batch
from app.modules.lorawan.crypto import (
    SCHEMA_VERSION_V1,
    CredentialsEncryptionContext,
    LoRaWanCredentialsCipher,
    resolve_encryption_key,
)
from app.modules.lorawan.schemas import Credentials

from ..exceptions import (
    KgLoRaWanConfigurationMissingError,
    KgLoRaWanCredentialsNotFoundError,
    KgNotFoundError,
)
from ..models import KgUnit
from ..repositories.credentials import LoRaWanCredentialsRepository


class LoRaWanCredentialsService:
    """Save and load a KG unit's typed credentials in a caller-owned transaction."""

    def __init__(self, session: AsyncSession, encryption_key: SecretStr | None) -> None:
        self._session = session
        self._repository = LoRaWanCredentialsRepository(session)
        self._cipher = LoRaWanCredentialsCipher(
            resolve_encryption_key(encryption_key)
        )

    async def save_credentials(
        self,
        *,
        kg_dev_eui: str,
        credentials: Credentials,
    ) -> None:
        context = await self._context_for_kg(kg_dev_eui)
        encrypted_data = self._cipher.encrypt_credentials(credentials, context)

        await self._repository.save(
            kg_dev_eui=kg_dev_eui,
            schema_version=SCHEMA_VERSION_V1,
            encrypted_data=encrypted_data,
        )

    async def credentials_exist(
        self,
        *,
        kg_dev_eui: str,
    ) -> bool:
        return await self._repository.exists(kg_dev_eui)

    async def load_credentials(
        self,
        *,
        kg_dev_eui: str,
    ) -> Credentials:
        context = await self._context_for_kg(kg_dev_eui)
        stored = await self._repository.get(kg_dev_eui)

        if stored is None:
            raise KgLoRaWanCredentialsNotFoundError

        return self._cipher.decrypt_credentials(
            stored.encrypted_data,
            stored.schema_version,
            context,
        )

    async def _context_for_kg(self, kg_dev_eui: str) -> CredentialsEncryptionContext:
        result = await self._session.execute(
            select(KgUnit)
            .where(KgUnit.dev_eui == kg_dev_eui)
            .options(selectinload(KgUnit.batch).selectinload(Batch.lorawan_config))
        )
        kg = result.scalar_one_or_none()

        if kg is None:
            raise KgNotFoundError

        if kg.batch.lorawan_config is None:
            raise KgLoRaWanConfigurationMissingError

        return CredentialsEncryptionContext(
            kg_dev_eui=kg.dev_eui,
            activation_type=kg.batch.lorawan_config.activation_type,
            lorawan_version=kg.batch.lorawan_config.lorawan_version,
        )
