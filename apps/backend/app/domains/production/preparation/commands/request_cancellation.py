from ..model import BatchKeyGenerationJob, BatchKeyGenerationStatus
from ..repository import PreparationRepository


async def request_cancellation(
    repository: PreparationRepository, job: BatchKeyGenerationJob
) -> BatchKeyGenerationJob:
    """Deletion owns cleanup; preparation only persists its stop signal."""
    if job.status is BatchKeyGenerationStatus.READY:
        return job
    return await repository.request_cancellation(job)
