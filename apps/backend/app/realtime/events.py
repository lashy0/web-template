from pydantic import BaseModel, JsonValue

from app.core.config import Settings
from app.infrastructure.redis.keys import build_redis_key


class RealtimeEvent(BaseModel):
    """The JSON payload sent through Redis and delivered over SSE."""

    type: str
    data: dict[str, JsonValue]


def events_channel(settings: Settings) -> str:
    return build_redis_key(settings, "events")


def format_sse_event(event: RealtimeEvent) -> str:
    """Encode an event as one Server-Sent Events data message."""
    return f"data: {event.model_dump_json()}\n\n"
