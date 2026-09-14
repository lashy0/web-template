from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contexts.production.batches.model import Batch
from app.modules.kg.models import KgUnit, LoRaWanCredentials

from .model import BatchKeyGenerationJob, BatchKeyGenerationStatus


class PreparationRepository:
    """SQL and lock primitives; callers own the surrounding transaction."""

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

    async def lock_batch(self, batch_id: UUID) -> Batch | None:
        result = await self._session.execute(
            select(Batch)
            .where(Batch.id == batch_id)
            .options(selectinload(Batch.lorawan_config))
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        job: BatchKeyGenerationJob,
        *,
        status: BatchKeyGenerationStatus,
        progress: int,
        error_code: str | None = None,
    ) -> BatchKeyGenerationJob:
        job.status = status
        job.progress = progress
        job.error_code = error_code
        await self._session.flush()
        return job

    async def request_cancellation(self, job: BatchKeyGenerationJob) -> BatchKeyGenerationJob:
        job.status = BatchKeyGenerationStatus.CANCELLING
        job.error_code = None
        await self._session.flush()
        return job

    async def claim_without_credentials(self, batch_id: UUID, *, limit: int) -> list[KgUnit]:
        result = await self._session.execute(
            select(KgUnit)
            .outerjoin(LoRaWanCredentials, LoRaWanCredentials.kg_dev_eui == KgUnit.dev_eui)
            .where(KgUnit.batch_id == batch_id, LoRaWanCredentials.kg_dev_eui.is_(None))
            .order_by(KgUnit.dev_eui.asc())
            .limit(limit)
            .with_for_update(of=KgUnit)
        )
        return list(result.scalars())

    async def count_credentials(self, batch_id: UUID) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(KgUnit)
            .join(LoRaWanCredentials, LoRaWanCredentials.kg_dev_eui == KgUnit.dev_eui)
            .where(KgUnit.batch_id == batch_id)
        )
        return int(count or 0)
