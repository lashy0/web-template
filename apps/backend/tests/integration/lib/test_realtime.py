"""Event delivery between processes, through a real Redis."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar, Protocol
from uuid import uuid4

import msgspec
import pytest
from pydantic import RedisDsn
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import Settings, get_settings
from app.lib.realtime import Realtime, RealtimeEvent, RealtimeMessage, create_realtime

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from pytest_databases.docker.redis import RedisService

pytestmark = [pytest.mark.anyio, pytest.mark.integration]

# Nothing listens on the discard port, so connections are refused at once.
_UNREACHABLE = "redis://127.0.0.1:9/0"

THING_CHANGED = msgspec.json.encode(RealtimeMessage(type="thing.changed", data=msgspec.Raw(b'{"thingId":7}')))


class ThingChanged(RealtimeEvent):
    event_type: ClassVar[str] = "thing.changed"
    permission: ClassVar[str] = "things.read"

    thing_id: int


class Connect(Protocol):
    async def __call__(self) -> Realtime: ...


def _settings(url: str, prefix: str) -> Settings:
    settings = get_settings()

    return replace(
        settings,
        redis=settings.redis.model_copy(update={"redis_url_override": RedisDsn(url), "prefix": prefix}),
        realtime=settings.realtime.model_copy(update={"backend": "redis"}),
    )


@pytest.fixture
def redis_settings(redis_service: RedisService) -> Settings:
    """Settings on the test Redis, with channels of this test: pub/sub channels are shared by every database."""
    url = f"redis://{redis_service.host}:{redis_service.port}/{redis_service.db}"

    return _settings(url, prefix=f"test-{uuid4().hex}")


@pytest.fixture
async def redis(redis_service: RedisService) -> AsyncGenerator[Redis]:
    """A connection of the test itself, to watch and disturb the server."""
    async with Redis(host=redis_service.host, port=redis_service.port, db=redis_service.db) as redis:
        yield redis


@pytest.fixture
async def connect(redis_settings: Settings) -> AsyncGenerator[Connect]:
    """Return a helper that starts the delivery of one more process."""
    started: list[Realtime] = []

    async def _connect() -> Realtime:
        realtime = create_realtime(redis_settings)
        await realtime.start()
        started.append(realtime)

        return realtime

    yield _connect

    for realtime in started:
        await realtime.close()


async def _wait_subscribed(redis: Redis, channel: str) -> None:
    """Wait until Redis has a subscriber of ``channel``; a subscription is confirmed asynchronously."""
    async with asyncio.timeout(5):
        while dict(await redis.pubsub_numsub(channel)).get(channel.encode(), 0) == 0:  # pyright: ignore[reportUnknownMemberType]
            await asyncio.sleep(0.05)


async def test_event_published_by_one_process_reaches_a_subscriber_of_another(
    connect: Connect,
    redis: Redis,
) -> None:
    api, worker = await connect(), await connect()

    async with api.subscribe({"things.read"}) as subscriber:
        await _wait_subscribed(redis, api.channel("things.read"))
        await worker.publish(ThingChanged(thing_id=7))
        payload = await asyncio.wait_for(subscriber.get(), timeout=5)

    assert payload == THING_CHANGED


async def test_subscriber_keeps_receiving_after_the_connection_is_lost(connect: Connect, redis: Redis) -> None:
    api, worker = await connect(), await connect()

    async with api.subscribe({"things.read"}) as subscriber:
        await _wait_subscribed(redis, api.channel("things.read"))
        await redis.client_kill_filter(_type="pubsub")  # pyright: ignore[reportUnknownMemberType]
        await _wait_subscribed(redis, api.channel("things.read"))
        await worker.publish(ThingChanged(thing_id=7))
        payload = await asyncio.wait_for(subscriber.get(), timeout=5)

    assert payload == THING_CHANGED


async def test_publish_fails_when_redis_is_unreachable() -> None:
    realtime = create_realtime(_settings(_UNREACHABLE, prefix="test"))

    with pytest.raises(RedisError):
        await realtime.publish(ThingChanged(thing_id=7))

    await realtime.close()
