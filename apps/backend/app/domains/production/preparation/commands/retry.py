from app.domains.production.batches.model import Batch
from app.domains.production.batches.rules import ensure_management_allowed, ensure_not_archived
from app.shared.security import CurrentPrincipal

from ..model import BatchKeyGenerationJob, BatchKeyGenerationStatus
from ..repository import PreparationRepository
from ..rules import can_retry


class RetryPreparation:
    def __init__(self, repository: PreparationRepository) -> None:
        self._repository = repository

    async def execute(
        self, *, actor: CurrentPrincipal, batch: Batch
    ) -> tuple[BatchKeyGenerationJob | None, bool]:
        ensure_management_allowed(actor)
        ensure_not_archived(batch)
        job = await self._repository.get(batch.id, for_update=True)
        if job is None or not can_retry(batch=batch, status=job.status):
            return job, False
        await self._repository.update(
            job, status=BatchKeyGenerationStatus.CREATING, progress=0, error_code=None
        )
        return job, True
