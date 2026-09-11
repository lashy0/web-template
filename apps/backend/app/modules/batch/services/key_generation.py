from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from loguru import logger
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.redis.publisher import publish_event
from app.modules.kg.exceptions import KgLoRaWanCredentialsAlreadyExistError
from app.modules.kg.repositories import KgRepository
from app.modules.kg.services import LoRaWanCredentialsService
from app.modules.lorawan.domain import ActivationType, LoRaWanVersion
from app.modules.lorawan.generator import generate_credentials

from ..models import BatchKeyGenerationStatus
from ..repositories import BatchRepository

KEY_GENERATION_CHUNK_SIZE = 500
StatusPublisher = Callable[[UUID, BatchKeyGenerationStatus], None]


class BatchKeyGenerationService:
    """Generate missing encrypted LoRaWAN credentials for a batch."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        encryption_key: SecretStr | None,
        publish_status: StatusPublisher | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._encryption_key = encryption_key
        self._publish_status = publish_status or publish_key_generation_status

    async def generate(self, batch_id: UUID) -> None:
        try:
            start = await self._start_generation(batch_id)

            if start is None:
                return

            activation_type, lorawan_version, status_changed = start

            if status_changed:
                self._publish_status(batch_id, BatchKeyGenerationStatus.RUNNING)

            while await self._generate_next_chunk(
                batch_id=batch_id,
                activation_type=activation_type,
                lorawan_version=lorawan_version,
            ):
                pass

            if await self._set_status(batch_id, BatchKeyGenerationStatus.COMPLETED):
                self._publish_status(batch_id, BatchKeyGenerationStatus.COMPLETED)

        except Exception:
            if await self._set_status(batch_id, BatchKeyGenerationStatus.FAILED):
                self._publish_status(batch_id, BatchKeyGenerationStatus.FAILED)

            logger.bind(
                event="batch.key_generation_failed",
                batch_id=str(batch_id),
            ).exception("Batch LoRaWAN key generation failed")

            raise

    async def _start_generation(
        self,
        batch_id: UUID,
    ) -> tuple[ActivationType, LoRaWanVersion, bool] | None:
        async with self._session_factory() as session, session.begin():
            repository = BatchRepository(session)
            batch = await repository.get_by_id(batch_id, for_update=True)

            if batch is None:
                logger.bind(event="batch.key_generation_not_found", batch_id=str(batch_id)).warning(
                    "Batch for LoRaWAN key generation was not found"
                )

                return None

            if batch.key_generation_status is BatchKeyGenerationStatus.COMPLETED:
                return None

            if batch.lorawan_config is None:
                raise RuntimeError("Batch does not have a LoRaWAN configuration")

            status_changed = batch.key_generation_status is not BatchKeyGenerationStatus.RUNNING

            if status_changed:
                await repository.update_key_generation_status(
                    batch,
                    status=BatchKeyGenerationStatus.RUNNING,
                )

            return (
                batch.lorawan_config.activation_type,
                batch.lorawan_config.lorawan_version,
                status_changed,
            )

    async def _generate_next_chunk(
        self,
        *,
        batch_id: UUID,
        activation_type: ActivationType,
        lorawan_version: LoRaWanVersion,
    ) -> bool:
        async with self._session_factory() as session, session.begin():
            kg_units = await KgRepository(session).list_without_credentials_by_batch(
                batch_id,
                limit=KEY_GENERATION_CHUNK_SIZE,
            )

            if not kg_units:
                return False

            credentials_service = LoRaWanCredentialsService(session, self._encryption_key)
            for kg_unit in kg_units:
                credentials = generate_credentials(
                    kg_unit.dev_eui,
                    activation_type,
                    lorawan_version,
                )

                try:
                    await credentials_service.save_credentials(
                        kg_dev_eui=kg_unit.dev_eui,
                        credentials=credentials,
                    )

                except KgLoRaWanCredentialsAlreadyExistError:
                    # A concurrent duplicate task may have saved this unit first.
                    continue

        return True

    async def _set_status(
        self,
        batch_id: UUID,
        status: BatchKeyGenerationStatus,
    ) -> bool:
        async with self._session_factory() as session, session.begin():
            repository = BatchRepository(session)
            batch = await repository.get_by_id(batch_id, for_update=True)

            if batch is None or batch.key_generation_status is status:
                return False

            await repository.update_key_generation_status(batch, status=status)

        return True


def publish_key_generation_status(
    batch_id: UUID,
    status: BatchKeyGenerationStatus,
) -> None:
    publish_event(
        type="batch.key_generation_status",
        data={
            "batch_id": str(batch_id),
            "status": status.value,
        },
    )
