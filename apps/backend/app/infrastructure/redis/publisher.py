from redis import Redis

from app.core.config import Settings, get_settings
from app.infrastructure.redis.client import create_sync_redis_client
from app.realtime.events import RealtimeEvent, events_channel


def publish_event(
    *,
    type: str,
    data: dict[str, object],
    settings: Settings | None = None,
    redis_client: Redis | None = None,
) -> int:
    app_settings = settings or get_settings()
    event = RealtimeEvent.model_validate({"type": type, "data": data})
    client = redis_client or create_sync_redis_client(app_settings)
    owns_client = redis_client is None

    try:
        return client.publish(
            events_channel(app_settings),
            event.model_dump_json(),
        )

    finally:
        if owns_client:
            client.close()
