import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.core.config import Settings
from app.core.logging import setup_logging
from app.infrastructure.redis.client import create_redis_client
from app.realtime.broadcaster import EventBroadcaster
from app.realtime.events import events_channel
from app.realtime.subscriber import read_pubsub_events


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings: Settings = app.state.settings
    setup_logging(settings)

    redis = create_redis_client(settings)
    pubsub = redis.pubsub()
    broadcaster = EventBroadcaster()
    channel = events_channel(settings)

    await pubsub.subscribe(channel)

    reader_task = asyncio.create_task(read_pubsub_events(pubsub, broadcaster))
    app.state.broadcaster = broadcaster

    logger.bind(event="realtime_startup").info("Realtime application startup")

    try:
        yield

    finally:
        reader_task.cancel()

        try:
            await reader_task

        except asyncio.CancelledError:
            pass

        await pubsub.unsubscribe(channel)
        await pubsub.aclose()  # type: ignore[no-untyped-call]
        await redis.aclose()
        await logger.complete()
