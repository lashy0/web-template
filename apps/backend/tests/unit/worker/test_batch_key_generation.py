from __future__ import annotations

from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from app.contexts.production.preparation.model import BatchKeyGenerationStatus
from app.contexts.production.preparation.rules import can_process_chunk
from app.modules.batch.services.key_generation import publish_preparation_status


@pytest.mark.unit
def test_preparation_status_event_has_expected_payload(mocker: MockerFixture) -> None:
    publish_event = mocker.patch("app.infrastructure.redis.preparation_notifier.publish_event")
    batch_id = uuid4()

    publish_preparation_status(batch_id, BatchKeyGenerationStatus.GENERATING, 37)

    publish_event.assert_called_once_with(
        type="batch.preparation_updated",
        data={
            "batch_id": str(batch_id),
            "status": "GENERATING",
            "progress": 37,
        },
    )


@pytest.mark.unit
def test_worker_does_not_begin_a_next_chunk_after_observing_cancelling() -> None:
    assert not can_process_chunk(BatchKeyGenerationStatus.CANCELLING)
