"""Deprecated import compatibility for the migrated preparation workflow."""

from uuid import UUID

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.contexts.production.preparation.commands.process_chunk import KEY_GENERATION_CHUNK_SIZE
from app.contexts.production.preparation.model import BatchKeyGenerationStatus
from app.contexts.production.preparation.notifier import ProgressNotifier
from app.contexts.production.preparation.worker_entry import process_preparation_job
from app.infrastructure.redis.preparation_notifier import RedisProgressNotifier


def publish_preparation_status(
    batch_id: UUID, status: BatchKeyGenerationStatus, progress: int
) -> None:
    RedisProgressNotifier().publish(batch_id, status, progress)


class BatchKeyGenerationJobService:
    """Thin delegate retained for callers which have not updated their import yet."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        encryption_key: SecretStr | None,
        publish_status: object | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._encryption_key = encryption_key
        self._notifier: ProgressNotifier = (
            _CallbackNotifier(publish_status) if callable(publish_status) else RedisProgressNotifier()
        )

    async def prepare(self, batch_id: UUID) -> None:
        await process_preparation_job(
            self._session_factory,
            encryption_key=self._encryption_key,
            batch_id=batch_id,
            notifier=self._notifier,
        )

    async def generate(self, batch_id: UUID) -> None:
        await self.prepare(batch_id)


BatchKeyGenerationService = BatchKeyGenerationJobService
BatchPreparationService = BatchKeyGenerationJobService

__all__ = [
    "BatchKeyGenerationJobService",
    "BatchKeyGenerationService",
    "BatchPreparationService",
    "publish_preparation_status",
    "KEY_GENERATION_CHUNK_SIZE",
]


class _CallbackNotifier(ProgressNotifier):
    def __init__(self, callback: object) -> None:
        self._callback = callback

    def publish(self, batch_id: UUID, status: BatchKeyGenerationStatus, progress: int) -> None:
        callback = self._callback
        if callable(callback):
            callback(batch_id, status, progress)
