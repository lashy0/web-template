from uuid import UUID

from loguru import logger
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.contexts.production.kg.repository import KgRepository
from app.shared.uow import transaction

from ..model import BatchKeyGenerationStatus
from ..notifier import ProgressNotifier
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
        notifier: ProgressNotifier,
    ) -> None:
        self._session_factory = session_factory
        self._encryption_key = encryption_key
        self._notifier = notifier

    async def execute(self, batch_id: UUID) -> None:
        try:
            update = await self._start(batch_id)
            if update is not None:
                self._notify(batch_id, *update)
            while True:
                result = await ProcessChunk(
                    self._session_factory, encryption_key=self._encryption_key
                ).execute(batch_id)
                if result is None:
                    return
                if result.processed:
                    self._notify(batch_id, result.status, result.progress)
                    continue
                update = await self._mark_ready(batch_id)
                if update is not None:
                    self._notify(batch_id, *update)
                return
        except Exception:
            update = await mark_failed(self._session_factory, batch_id)
            if update is not None:
                self._notify(batch_id, *update)
            logger.bind(event="batch.preparation_failed", batch_id=str(batch_id)).exception(
                "Batch LoRaWAN key generation failed"
            )
            raise

    async def _start(self, batch_id: UUID) -> tuple[BatchKeyGenerationStatus, int] | None:
        async with transaction(self._session_factory) as session:
            repository = PreparationRepository(session)
            batch = await repository.lock_batch(batch_id)
            if batch is None:
                return None
            job = await repository.get(batch.id, for_update=True)
            if job is None or not can_start(job.status):
                return None
            await repository.update(
                job, status=BatchKeyGenerationStatus.GENERATING, progress=job.progress
            )
            return job.status, job.progress

    async def _mark_ready(self, batch_id: UUID) -> tuple[BatchKeyGenerationStatus, int] | None:
        async with transaction(self._session_factory) as session:
            repository = PreparationRepository(session)
            batch = await repository.lock_batch(batch_id)
            if batch is None:
                return None
            job = await repository.get(batch.id, for_update=True)
            if job is None:
                return None
            count = await KgRepository(session).count_credentials_for_batch(batch.id)
            if not can_mark_ready(status=job.status, count=count, planned_qty=batch.planned_qty):
                return None
            await repository.update(job, status=BatchKeyGenerationStatus.READY, progress=100)
            return job.status, job.progress

    def _notify(self, batch_id: UUID, status: BatchKeyGenerationStatus, progress: int) -> None:
        try:
            self._notifier.publish(batch_id, status, progress)
        except Exception:
            logger.bind(
                event="batch.preparation_notification_failed", batch_id=str(batch_id)
            ).exception("Could not publish committed batch preparation update")
