"""Narrow temporary production-internal bridges for not-yet-migrated subdomains."""

from collections.abc import Sequence
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.contexts.production.compat.kg_units import LegacyKgUnitBridge as LegacyKgUnitBridge
from app.modules.batch.models import BatchKeyGenerationJob, BatchKeyGenerationStatus
from app.modules.batch.services.key_generation import (
    KEY_GENERATION_FAILED_ERROR_CODE,
    publish_preparation_status,
)
from app.shared.uow import transaction
from app.worker.celery_app import celery_app

from .repository import BatchRepository

GENERATE_BATCH_KEYS_TASK = "app.worker.generate_batch_keys"

__all__ = [
    "LegacyKgUnitBridge",
    "LegacyPreparationBridge",
    "PreparationDispatcher",
]


class LegacyPreparationBridge:
    """Temporary read/write boundary for the future preparation subdomain."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_initial_job(self, batch_id: UUID) -> BatchKeyGenerationJob:
        job = BatchKeyGenerationJob(batch_id=batch_id)
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(
        self, batch_id: UUID, *, for_update: bool = False
    ) -> BatchKeyGenerationJob | None:
        return await self._session.get(
            BatchKeyGenerationJob,
            batch_id,
            with_for_update=for_update,
            populate_existing=for_update,
        )

    async def get_many(self, batch_ids: Sequence[UUID]) -> dict[UUID, BatchKeyGenerationJob]:
        if not batch_ids:
            return {}
        jobs = await self._session.scalars(
            select(BatchKeyGenerationJob).where(BatchKeyGenerationJob.batch_id.in_(batch_ids))
        )
        return {job.batch_id: job for job in jobs}

    async def request_cancellation(self, job: BatchKeyGenerationJob) -> BatchKeyGenerationJob:
        """Persist the legacy cancellation transition while preserving its semantics."""
        job.status = BatchKeyGenerationStatus.CANCELLING
        job.error_code = None
        await self._session.flush()
        return job


class PreparationDispatcher:
    """Post-commit worker dispatch retaining the legacy failure recovery semantics."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def dispatch_after_commit(self, batch_id: UUID) -> None:
        try:
            celery_app.send_task(GENERATE_BATCH_KEYS_TASK, args=[str(batch_id)])
        except Exception:
            logger.bind(
                event="batch.preparation_dispatch_failed", batch_id=str(batch_id)
            ).exception("Could not start batch KG preparation")
            async with transaction(self._session_factory) as session:
                batches = BatchRepository(session)
                batch = await batches.get(batch_id, for_update=True)
                if batch is None:
                    return
                job = await LegacyPreparationBridge(session).get(batch.id, for_update=True)
                if job is None:
                    return
                job.status = BatchKeyGenerationStatus.FAILED
                job.error_code = KEY_GENERATION_FAILED_ERROR_CODE
                await session.flush()
                publish_preparation_status(batch.id, job.status, job.progress)
            return
        publish_preparation_status(batch_id, BatchKeyGenerationStatus.CREATING, 0)
