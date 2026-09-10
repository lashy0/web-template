from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..exceptions import KgLoRaWanCredentialsAlreadyExistError
from ..models import LoRaWanCredentials


class LoRaWanCredentialsRepository:
    """Encrypted LoRaWAN credential persistence owned by KG units."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        *,
        kg_dev_eui: str,
        schema_version: int,
        encrypted_data: bytes,
    ) -> LoRaWanCredentials:
        if await self.exists(kg_dev_eui):
            raise KgLoRaWanCredentialsAlreadyExistError

        credentials = LoRaWanCredentials(
            kg_dev_eui=kg_dev_eui,
            schema_version=schema_version,
            encrypted_data=encrypted_data,
        )

        try:
            async with self._session.begin_nested():
                self._session.add(credentials)
                await self._session.flush()

        except IntegrityError as exc:
            # The primary key also protects against concurrent writers.
            raise KgLoRaWanCredentialsAlreadyExistError from exc

        return credentials

    async def exists(self, kg_dev_eui: str) -> bool:
        return bool(
            await self._session.scalar(
                select(exists().where(LoRaWanCredentials.kg_dev_eui == kg_dev_eui))
            )
        )

    async def get(self, kg_dev_eui: str) -> LoRaWanCredentials | None:
        return await self._session.get(LoRaWanCredentials, kg_dev_eui)
