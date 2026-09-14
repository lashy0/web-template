from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from app.modules.batch.models import BatchKeyGenerationStatus
from app.modules.batch.services.key_generation import (
    BatchKeyGenerationService,
    publish_preparation_status,
)


class _Transaction:
    async def __aenter__(self) -> _Transaction:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class _Session:
    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def begin(self) -> _Transaction:
        return _Transaction()


class _SessionFactory:
    def __call__(self) -> _Session:
        return _Session()


@pytest.mark.unit
def test_preparation_status_event_has_expected_payload(mocker: MockerFixture) -> None:
    publish_event = mocker.patch("app.modules.batch.services.key_generation.publish_event")
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
async def test_worker_does_not_generate_a_next_chunk_after_observing_cancelling(
    mocker: MockerFixture,
) -> None:
    batch_id = uuid4()
    batches = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(id=batch_id)),
        get_key_generation_job=AsyncMock(
            return_value=SimpleNamespace(status=BatchKeyGenerationStatus.CANCELLING)
        ),
    )
    repository = mocker.patch("app.modules.batch.services.key_generation.BatchRepository")
    repository.return_value = batches
    kg_repository = mocker.patch("app.modules.batch.services.key_generation.KgRepository")

    update = await BatchKeyGenerationService(
        _SessionFactory(),  # type: ignore[arg-type]
        encryption_key=None,
    )._generate_next_chunk(batch_id)

    assert update is None
    batches.get_by_id.assert_awaited_once_with(batch_id, for_update=True)
    batches.get_key_generation_job.assert_awaited_once_with(batch_id, for_update=True)
    kg_repository.assert_not_called()
