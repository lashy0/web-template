from uuid import UUID

from loguru import logger
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domains.production.kg.repository import KgRepository
from app.shared.uow import PostCommitExecutor, transaction

from ..effects import PublishPreparationProgress
from ..model import BatchKeyGenerationStatus
from ..repository import PreparationRepository
from ..rules import can_mark_ready, can_start
from .mark_failed import mark_failed
from .process_chunk import ProcessChunk


class ProcessJob:
    """Coordinate short committed transitions/chunks for one worker invocation."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        encryption_key: SecretStr | None,
        effect_executor: PostCommitExecutor,
    ) -> None:
        self._session_factory = session_factory
        self._encryption_key = encryption_key
        self._effect_executor = effect_executor

    async def execute(self, batch_id: UUID) -> None:
        try:
            await self._start(batch_id)
            while True:
                result = await ProcessChunk(
                    self._session_factory,
                    encryption_key=self._encryption_key,
                    effect_executor=self._effect_executor,
                ).execute(batch_id)
                if result is None:
                    return
                if result.processed:
                    continue
                await self._mark_ready(batch_id)
                return
        except Exception:
            await mark_failed(
                self._session_factory, batch_id, effect_executor=self._effect_executor
            )
            logger.bind(event="batch.preparation_failed", batch_id=str(batch_id)).exception(
                "Batch LoRaWAN key generation failed"
            )
            raise

    async def _start(self, batch_id: UUID) -> None:
        async with transaction(self._session_factory, executor=self._effect_executor) as uow:
            session = uow.session
            repository = PreparationRepository(session)
            batch = await repository.lock_batch(batch_id)
            if batch is None:
                return
            job = await repository.get(batch.id, for_update=True)
            if job is None or not can_start(job.status):
                return
            await repository.update(
                job, status=BatchKeyGenerationStatus.GENERATING, progress=job.progress
            )
            uow.after_commit(PublishPreparationProgress(batch_id, job.status, job.progress))

    async def _mark_ready(self, batch_id: UUID) -> None:
        async with transaction(self._session_factory, executor=self._effect_executor) as uow:
            session = uow.session
            repository = PreparationRepository(session)
            batch = await repository.lock_batch(batch_id)
            if batch is None:
                return
            job = await repository.get(batch.id, for_update=True)
            if job is None:
                return
            count = await KgRepository(session).count_credentials_for_batch(batch.id)
            if not can_mark_ready(status=job.status, count=count, planned_qty=batch.planned_qty):
                return
            await repository.update(job, status=BatchKeyGenerationStatus.READY, progress=100)
            uow.after_commit(PublishPreparationProgress(batch_id, job.status, job.progress))
