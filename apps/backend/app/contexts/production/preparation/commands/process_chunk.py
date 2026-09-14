from dataclasses import dataclass
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.components.keygen import generate_credentials
from app.modules.kg.exceptions import KgLoRaWanCredentialsAlreadyExistError
from app.shared.uow import transaction

from ..credentials import PreparationCredentials
from ..model import BatchKeyGenerationStatus
from ..repository import PreparationRepository
from ..rules import can_process_chunk, progress_for

KEY_GENERATION_CHUNK_SIZE = 500


@dataclass(frozen=True, slots=True)
class ChunkResult:
    status: BatchKeyGenerationStatus
    progress: int
    processed: bool


class ProcessChunk:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], *, encryption_key: SecretStr | None
    ) -> None:
        self._session_factory = session_factory
        self._encryption_key = encryption_key

    async def execute(self, batch_id: UUID) -> ChunkResult | None:
        async with transaction(self._session_factory) as session:
            repository = PreparationRepository(session)
            batch = await repository.lock_batch(batch_id)
            if batch is None:
                return None
            job = await repository.get(batch.id, for_update=True)
            if job is None or not can_process_chunk(job.status):
                return None
            units = await repository.claim_without_credentials(
                batch.id, limit=KEY_GENERATION_CHUNK_SIZE
            )
            if not units:
                return ChunkResult(job.status, job.progress, processed=False)
            config = batch.lorawan_config
            if config is None:
                raise RuntimeError("Batch does not have a LoRaWAN configuration")
            credentials = PreparationCredentials(session, self._encryption_key)
            for unit in units:
                try:
                    await credentials.save(
                        batch=batch,
                        kg_dev_eui=unit.dev_eui,
                        credentials=generate_credentials(
                            unit.dev_eui, config.activation_type, config.lorawan_version
                        ),
                    )
                except KgLoRaWanCredentialsAlreadyExistError:
                    continue
            count = await repository.count_credentials(batch.id)
            progress = progress_for(credential_count=count, planned_qty=batch.planned_qty)
            await repository.update(
                job, status=BatchKeyGenerationStatus.GENERATING, progress=progress
            )
            return ChunkResult(job.status, progress, processed=True)
