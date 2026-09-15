from types import SimpleNamespace

from app.domains.production.preparation.commands.process_chunk import KEY_GENERATION_CHUNK_SIZE
from app.domains.production.preparation.model import BatchKeyGenerationStatus
from app.domains.production.preparation.rules import (
    can_mark_failed,
    can_mark_ready,
    can_process_chunk,
    can_retry,
    can_start,
    progress_for,
)


def test_transition_guards_preserve_the_preparation_table() -> None:
    batch = SimpleNamespace(archived_at=None)

    assert can_retry(batch=batch, status=BatchKeyGenerationStatus.FAILED)
    assert not can_retry(batch=batch, status=BatchKeyGenerationStatus.CREATING)
    assert not can_retry(
        batch=SimpleNamespace(archived_at=object()), status=BatchKeyGenerationStatus.FAILED
    )
    assert can_start(BatchKeyGenerationStatus.CREATING)
    assert not can_start(BatchKeyGenerationStatus.GENERATING)
    assert can_process_chunk(BatchKeyGenerationStatus.GENERATING)
    assert not can_process_chunk(BatchKeyGenerationStatus.CANCELLING)


def test_completion_and_failure_guards_are_exact() -> None:
    assert can_mark_ready(status=BatchKeyGenerationStatus.GENERATING, count=5, planned_qty=5)
    assert not can_mark_ready(status=BatchKeyGenerationStatus.GENERATING, count=4, planned_qty=5)
    assert not can_mark_ready(status=BatchKeyGenerationStatus.CANCELLING, count=5, planned_qty=5)
    assert can_mark_failed(BatchKeyGenerationStatus.CREATING)
    assert can_mark_failed(BatchKeyGenerationStatus.GENERATING)
    assert not can_mark_failed(BatchKeyGenerationStatus.CANCELLING)
    assert not can_mark_failed(BatchKeyGenerationStatus.READY)


def test_progress_is_derived_from_durable_credential_count_and_chunk_is_bounded() -> None:
    assert KEY_GENERATION_CHUNK_SIZE == 500
    assert progress_for(credential_count=2, planned_qty=3) == 66
