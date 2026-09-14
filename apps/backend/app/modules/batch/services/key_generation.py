from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from loguru import logger
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.components.keygen.generator import generate_credentials
from app.infrastructure.redis.publisher import publish_event
from app.modules.kg.exceptions import KgLoRaWanCredentialsAlreadyExistError
from app.modules.kg.repositories import KgRepository
from app.modules.kg.services import LoRaWanCredentialsService

from ..models import BatchKeyGenerationStatus
from ..repositories import BatchRepository

KEY_GENERATION_CHUNK_SIZE = 500
KEY_GENERATION_FAILED_ERROR_CODE = "batch_key_generation_failed"
StatusPublisher = Callable[[UUID, BatchKeyGenerationStatus, int], None]


@dataclass(frozen=True, slots=True)
class PreparationUpdate:
    status: BatchKeyGenerationStatus
    progress: int


class BatchKeyGenerationJobService:
    """Generate LoRaWAN credentials for KG rows created with the batch."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        encryption_key: SecretStr | None,
        publish_status: StatusPublisher | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._encryption_key = encryption_key
        self._publish_status = publish_status or publish_preparation_status

    async def prepare(self, batch_id: UUID) -> None:
        try:
            while (update := await self._generate_next_chunk(batch_id)) is not None:
                self._publish(update, batch_id)

            if (update := await self._mark_ready(batch_id)) is not None:
                self._publish(update, batch_id)

        except Exception:
            if (update := await self._mark_failed(batch_id)) is not None:
                self._publish(update, batch_id)

            logger.bind(
                event="batch.preparation_failed",
                batch_id=str(batch_id),
            ).exception("Batch LoRaWAN key generation failed")

            raise

    async def generate(self, batch_id: UUID) -> None:
        await self.prepare(batch_id)

    async def _generate_next_chunk(self, batch_id: UUID) -> PreparationUpdate | None:
        async with self._session_factory() as session, session.begin():
            batches = BatchRepository(session)
            batch = await batches.get_by_id(batch_id, for_update=True)

            if batch is None:
                return None

            job = await batches.get_key_generation_job(batch_id, for_update=True)

            if job is None:
                return None

            if job.status is BatchKeyGenerationStatus.CREATING:
                await batches.update_key_generation_job(
                    job,
                    status=BatchKeyGenerationStatus.GENERATING,
                    progress=job.progress,
                )

                return PreparationUpdate(BatchKeyGenerationStatus.GENERATING, job.progress)

            if job.status is not BatchKeyGenerationStatus.GENERATING:
                return None

            if batch.lorawan_config is None:
                raise RuntimeError("Batch does not have a LoRaWAN configuration")

            kg = KgRepository(session)
            kg_units = await kg.list_without_credentials_by_batch(
                batch_id,
                limit=KEY_GENERATION_CHUNK_SIZE,
            )

            if not kg_units:
                return None

            credentials_service = LoRaWanCredentialsService(session, self._encryption_key)

            for kg_unit in kg_units:
                credentials = generate_credentials(
                    kg_unit.dev_eui,
                    batch.lorawan_config.activation_type,
                    batch.lorawan_config.lorawan_version,
                )

                try:
                    await credentials_service.save_credentials(
                        kg_dev_eui=kg_unit.dev_eui,
                        credentials=credentials,
                    )

                except KgLoRaWanCredentialsAlreadyExistError:
                    continue

            generated_count = await kg.count_with_credentials_by_batch(batch.id)
            progress = generated_count * 100 // batch.planned_qty

            await batches.update_key_generation_job(
                job,
                status=BatchKeyGenerationStatus.GENERATING,
                progress=progress,
            )

            return PreparationUpdate(BatchKeyGenerationStatus.GENERATING, progress)

    async def _mark_ready(self, batch_id: UUID) -> PreparationUpdate | None:
        async with self._session_factory() as session, session.begin():
            batches = BatchRepository(session)
            batch = await batches.get_by_id(batch_id, for_update=True)

            if batch is None:
                return None

            job = await batches.get_key_generation_job(batch_id, for_update=True)

            if job is None or job.status is not BatchKeyGenerationStatus.GENERATING:
                return None

            credentials_count = await KgRepository(session).count_with_credentials_by_batch(
                batch.id
            )

            if credentials_count != batch.planned_qty:
                return None

            await batches.update_key_generation_job(
                job,
                status=BatchKeyGenerationStatus.READY,
                progress=100,
            )

            return PreparationUpdate(BatchKeyGenerationStatus.READY, 100)

    async def _mark_failed(self, batch_id: UUID) -> PreparationUpdate | None:
        async with self._session_factory() as session, session.begin():
            batches = BatchRepository(session)
            batch = await batches.get_by_id(batch_id, for_update=True)

            if batch is None:
                return None

            job = await batches.get_key_generation_job(batch_id, for_update=True)

            if job is None or job.status is BatchKeyGenerationStatus.CANCELLING:
                return None

            await batches.update_key_generation_job(
                job,
                status=BatchKeyGenerationStatus.FAILED,
                progress=job.progress,
                error_code=KEY_GENERATION_FAILED_ERROR_CODE,
            )

            return PreparationUpdate(BatchKeyGenerationStatus.FAILED, job.progress)

    def _publish(self, update: PreparationUpdate, batch_id: UUID) -> None:
        self._publish_status(batch_id, update.status, update.progress)


# The old names remain import-compatible for queued tasks and integrations.
BatchKeyGenerationService = BatchKeyGenerationJobService
BatchPreparationService = BatchKeyGenerationJobService


def publish_preparation_status(
    batch_id: UUID,
    status: BatchKeyGenerationStatus,
    progress: int,
) -> None:
    publish_event(
        type="batch.preparation_updated",
        data={
            "batch_id": str(batch_id),
            "status": status.value,
            "progress": progress,
        },
    )
