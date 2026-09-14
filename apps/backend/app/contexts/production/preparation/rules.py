from app.contexts.production.batches.model import Batch

from .model import BatchKeyGenerationStatus


def can_retry(*, batch: Batch, status: BatchKeyGenerationStatus | None) -> bool:
    return batch.archived_at is None and status is BatchKeyGenerationStatus.FAILED


def can_start(status: BatchKeyGenerationStatus) -> bool:
    return status is BatchKeyGenerationStatus.CREATING


def can_process_chunk(status: BatchKeyGenerationStatus) -> bool:
    return status is BatchKeyGenerationStatus.GENERATING


def can_mark_ready(*, status: BatchKeyGenerationStatus, count: int, planned_qty: int) -> bool:
    return status is BatchKeyGenerationStatus.GENERATING and count == planned_qty


def can_mark_failed(status: BatchKeyGenerationStatus) -> bool:
    return status in (BatchKeyGenerationStatus.CREATING, BatchKeyGenerationStatus.GENERATING)


def progress_for(*, credential_count: int, planned_qty: int) -> int:
    return credential_count * 100 // planned_qty
