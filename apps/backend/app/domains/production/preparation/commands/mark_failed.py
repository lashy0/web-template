from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.uow import PostCommitExecutor, transaction

from ..effects import PublishPreparationProgress
from ..model import BatchKeyGenerationStatus
from ..repository import PreparationRepository
from ..rules import can_mark_failed

KEY_GENERATION_FAILED_ERROR_CODE = "batch_key_generation_failed"


async def mark_failed(
    session_factory: async_sessionmaker[AsyncSession],
    batch_id: UUID,
    *,
    effect_executor: PostCommitExecutor | None = None,
) -> tuple[BatchKeyGenerationStatus, int] | None:
    """Commit FAILED before exposing it to the best-effort notifier."""
    async with transaction(session_factory, executor=effect_executor) as uow:
        session = uow.session
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
        uow.after_commit(PublishPreparationProgress(batch_id, job.status, job.progress))
        return job.status, job.progress
