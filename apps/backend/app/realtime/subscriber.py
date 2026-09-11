from typing import Any

from loguru import logger
from redis.asyncio.client import PubSub

from app.realtime.broadcaster import EventBroadcaster
from app.realtime.events import RealtimeEvent


def forward_redis_message(message: dict[str, Any], broadcaster: EventBroadcaster) -> None:
    """Validate a Redis Pub/Sub message before making it visible to clients."""
    if message.get("type") != "message":
        return

    payload = message.get("data")

    if not isinstance(payload, str):
        logger.bind(event="realtime.invalid_event").warning("Redis event is not text")
        return

    try:
        event = RealtimeEvent.model_validate_json(payload)

    except ValueError:
        logger.bind(event="realtime.invalid_event").warning("Redis event has an invalid format")
        return

    broadcaster.broadcast(event)


async def read_pubsub_events(pubsub: PubSub, broadcaster: EventBroadcaster) -> None:
    async for message in pubsub.listen():
        forward_redis_message(message, broadcaster)
