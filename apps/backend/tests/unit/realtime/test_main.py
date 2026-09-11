from typing import cast

import pytest
from fastapi.testclient import TestClient
from redis import Redis

from app.core.config import Settings
from app.infrastructure.redis.publisher import publish_event
from app.realtime.broadcaster import EventBroadcaster
from app.realtime.main import create_app
from app.realtime.subscriber import forward_redis_message


class FakeRedis:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        return 1


@pytest.mark.unit
def test_health_returns_ok() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
async def test_redis_event_is_converted_to_sse_event() -> None:
    broadcaster = EventBroadcaster()
    first_client_queue = broadcaster.subscribe()
    second_client_queue = broadcaster.subscribe()

    forward_redis_message(
        {
            "type": "message",
            "data": '{"type":"test.event","data":{"message":"hello"}}',
        },
        broadcaster,
    )

    expected_event = 'data: {"type":"test.event","data":{"message":"hello"}}\n\n'
    assert await first_client_queue.get() == expected_event
    assert await second_client_queue.get() == expected_event


@pytest.mark.unit
def test_publish_event_uses_prefixed_redis_channel() -> None:
    settings = Settings.model_validate({"BACKEND_REDIS_PREFIX": "test-app"})
    redis = FakeRedis()

    recipients = publish_event(
        type="test.event",
        data={"message": "hello"},
        settings=settings,
        redis_client=cast(Redis, redis),
    )

    assert recipients == 1
    assert redis.published == [
        ("test-app:events", '{"type":"test.event","data":{"message":"hello"}}')
    ]
