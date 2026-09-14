"""Realtime adapter compatibility boundary."""

from app.infrastructure.redis.publisher import publish_event
from app.realtime.main import create_app as create_realtime_app

__all__ = ["create_realtime_app", "publish_event"]
