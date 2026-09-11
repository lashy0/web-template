from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from app.modules.batch.models import BatchKeyGenerationStatus
from app.modules.batch.services.key_generation import publish_key_generation_status


@pytest.mark.unit
def test_key_generation_status_event_has_expected_payload(mocker: MockerFixture) -> None:
    publish_event = mocker.patch("app.modules.batch.services.key_generation.publish_event")
    batch_id = uuid4()

    publish_key_generation_status(batch_id, BatchKeyGenerationStatus.RUNNING)

    publish_event.assert_called_once_with(
        type="batch.key_generation_status",
        data={
            "batch_id": str(batch_id),
            "status": "RUNNING",
        },
    )
