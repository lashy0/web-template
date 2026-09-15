from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.uow import transaction

from ..model import BatchKeyGenerationStatus
from ..repository import PreparationRepository
from ..rules import can_mark_failed

KEY_GENERATION_FAILED_ERROR_CODE = "batch_key_generation_failed"


async def mark_failed(
    session_factory: async_sessionmaker[AsyncSession], batch_id: UUID
) -> tuple[BatchKeyGenerationStatus, int] | None:
    """Commit FAILED before exposing it to the best-effort notifier."""
    async with transaction(session_factory) as session:
        repository = PreparationRepository(session)
        batch = await repository.lock_batch(batch_id)
        if batch is None:
            return None
        job = await repository.get(batch.id, for_update=True)
        if job is None or not can_mark_failed(job.status):
            return None
        await repository.update(
            job,
            status=BatchKeyGenerationStatus.FAILED,
            progress=job.progress,
            error_code=KEY_GENERATION_FAILED_ERROR_CODE,
        )
        return job.status, job.progress
