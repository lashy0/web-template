"""Realtime events: changes announced to browsers over server-sent events.

Litestar's ``ChannelsPlugin`` delivers them between processes. Every
permission has a channel: an event goes to the channel of the permission it
needs, and a stream subscribes to the channels of the user's permissions.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Set
from contextlib import asynccontextmanager
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar, Final, cast

import msgspec
import structlog
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.channels.backends.redis import RedisChannelsPubSubBackend
from litestar.channels.subscriber import Subscriber
from litestar.response import ServerSentEventMessage
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

from app.lib.schema import CamelizedBaseStruct

if TYPE_CHECKING:
    from litestar.channels.backends.base import ChannelsBackend

    from app.config import Settings
    from app.lib.uow import UnitOfWork

logger = structlog.get_logger()

RESYNC_EVENT: Final = "resync"
HEARTBEAT_SECONDS: Final = 20.0
STREAM_LIFETIME_SECONDS: Final = 15 * 60.0

_MAX_BACKLOG: Final = 256
_REDIS_TIMEOUT_SECONDS: Final = 2.0
_HEALTH_CHECK_SECONDS: Final = 30.0
_RECONNECT_MIN_SECONDS: Final = 1.0
_RECONNECT_MAX_SECONDS: Final = 30.0


class RealtimeEvent(CamelizedBaseStruct):
    """A change announced to the users who hold ``permission``.

    An event says what changed, not the new state: a client reads the state
    again. Events are not stored, so one published while nobody listens is
    lost, and a client rereads everything when its stream opens.
    """

    event_type: ClassVar[str]
    permission: ClassVar[str]


class RealtimeMessage(msgspec.Struct, frozen=True):
    """An event as it travels through a channel."""

    type: str
    data: msgspec.Raw


RESYNC: Final = RealtimeMessage(type=RESYNC_EVENT, data=msgspec.Raw(b"{}"))
"""Tells a client that events may have been lost, so it rereads what it shows."""

_RESYNC_PAYLOAD: Final = msgspec.json.encode(RESYNC)


class ResyncSubscriber(Subscriber):
    """The events one stream has yet to read.

    A reader this far behind rereads everything instead of catching up: a full
    backlog is replaced by one resync. Litestar's own backlog strategies drop
    events without a word.
    """

    def put_nowait(self, item: bytes | None) -> bool:
        if self._queue.full():
            while not self._queue.empty():
                self._queue.get_nowait()
                self._queue.task_done()

            # ``None`` ends the subscription and must still arrive.
            if item is not None:
                item = _RESYNC_PAYLOAD

        return super().put_nowait(item)

    async def put(self, item: bytes | None) -> None:
        # The plugin awaits room for the ``None`` that ends a subscription; never block it.
        self.put_nowait(item)

    async def get(self) -> bytes | None:
        """Wait for the next message; ``None`` once the subscription has ended."""
        item = cast("bytes | None", await self._queue.get())
        self._queue.task_done()

        return item


class ListeningRedisBackend(RedisChannelsPubSubBackend):
    """Redis pub/sub that keeps listening after Redis fails.

    The plugin reads :meth:`stream_events` in one task, which a Redis error
    would end for good. Here the listener waits, 1 to 30 seconds, and reads
    again; redis-py then reconnects and subscribes to the channels anew. What
    was published in between is lost.
    """

    async def stream_events(self) -> AsyncGenerator[tuple[str, Any]]:
        delay = _RECONNECT_MIN_SECONDS

        while True:
            try:
                async for event in super().stream_events():
                    delay = _RECONNECT_MIN_SECONDS
                    yield event
            except RedisError:
                logger.warning("realtime.listener_failed", retry_in=delay, exc_info=True)

            await asyncio.sleep(delay)
            delay = min(delay * 2, _RECONNECT_MAX_SECONDS)

    async def on_shutdown(self) -> None:
        pub_sub: Any = self._pub_sub
        await pub_sub.aclose()


class Realtime:
    """Publish events and subscribe to them through the channels of their permissions.

    ``channels`` is the plugin that delivers them: an application runs it in
    its lifespan, a worker with :meth:`start`.
    """

    __slots__ = ("_prefix", "_redis", "_started", "channels")

    def __init__(self, channels: ChannelsPlugin, *, prefix: str, redis: Redis | None = None) -> None:
        self.channels = channels
        self._prefix = prefix
        self._redis = redis
        self._started = False

    def channel(self, permission: str) -> str:
        """The channel of the events that need ``permission``."""
        return f"{self._prefix}:{permission}"

    async def publish(self, event: RealtimeEvent) -> None:
        """Announce ``event``.

        Raises:
            redis.exceptions.RedisError: Redis did not take the event; it is lost.
        """
        message = RealtimeMessage(type=event.event_type, data=msgspec.Raw(msgspec.json.encode(event)))

        await self.channels.wait_published(  # pyright: ignore[reportUnknownMemberType]
            msgspec.json.encode(message),
            self.channel(event.permission),
        )

    @asynccontextmanager
    async def subscribe(self, permissions: Set[str]) -> AsyncGenerator[ResyncSubscriber]:
        """Collect, while the block runs, the events a user with ``permissions`` may receive."""
        names = [self.channel(permission) for permission in permissions]
        subscriber = cast("ResyncSubscriber", await self.channels.subscribe(names))

        try:
            yield subscriber
        finally:
            # A stream ends by cancellation, and the plugin must still forget the subscriber.
            await asyncio.shield(self.channels.unsubscribe(subscriber, names))

    async def start(self) -> None:
        """Start the delivery outside an application's lifespan, as a worker does."""
        await self.channels.__aenter__()
        self._started = True

    async def close(self) -> None:
        """Stop the delivery started with :meth:`start` and close the Redis connections."""
        if self._started:
            self._started = False
            await self.channels.__aexit__(None, None, None)

        if self._redis is not None:
            await self._redis.aclose()


def announce_after_commit(uow: UnitOfWork, realtime: Realtime, event: RealtimeEvent) -> None:
    """Publish ``event`` once the transaction commits, so a client that rereads on it sees the change."""
    uow.after_commit(f"realtime.{event.event_type}", partial(realtime.publish, event))


def create_realtime(settings: Settings) -> Realtime:
    """Build the event delivery of ``settings``; Redis is contacted on first use."""
    prefix = f"{settings.redis.prefix}:events"

    if settings.realtime.backend == "memory":
        return Realtime(_create_channels(MemoryChannelsBackend()), prefix=prefix)

    redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        str(settings.redis.url),
        # Publishing is part of a request: fail fast rather than hold the response.
        socket_connect_timeout=_REDIS_TIMEOUT_SECONDS,
        socket_timeout=_REDIS_TIMEOUT_SECONDS,
        retry=Retry(NoBackoff(), 0),
        health_check_interval=_HEALTH_CHECK_SECONDS,
    )

    return Realtime(_create_channels(ListeningRedisBackend(redis=redis)), prefix=prefix, redis=redis)


def _create_channels(backend: ChannelsBackend) -> ChannelsPlugin:
    return ChannelsPlugin(
        backend=backend,
        arbitrary_channels_allowed=True,
        subscriber_max_backlog=_MAX_BACKLOG,
        subscriber_class=ResyncSubscriber,
    )


async def event_stream(
    realtime: Realtime,
    granted: Set[str],
    *,
    heartbeat: float = HEARTBEAT_SECONDS,
    lifetime: float = STREAM_LIFETIME_SECONDS,
) -> AsyncGenerator[ServerSentEventMessage]:
    """Yield the events a user with the ``granted`` permissions may receive.

    The stream opens with a resync: only from then on is nothing missed. An
    idle stream carries a comment every ``heartbeat`` seconds, so proxies keep
    it open and a closed connection is noticed. The stream ends after
    ``lifetime``: the browser then reconnects and is authenticated again.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + lifetime

    async with realtime.subscribe(granted) as subscriber:
        yield ServerSentEventMessage(event=RESYNC.type, data=bytes(RESYNC.data))

        while (remaining := deadline - loop.time()) > 0:
            try:
                payload = await asyncio.wait_for(subscriber.get(), timeout=min(heartbeat, remaining))
            except TimeoutError:
                yield ServerSentEventMessage(comment="ping", data=None)
                continue

            if payload is None:
                return

            try:
                message = msgspec.json.decode(payload, type=RealtimeMessage)
            except msgspec.MsgspecError:
                logger.warning("realtime.message_malformed")
                continue

            yield ServerSentEventMessage(event=message.type, data=bytes(message.data))


__all__ = (
    "HEARTBEAT_SECONDS",
    "RESYNC",
    "RESYNC_EVENT",
    "STREAM_LIFETIME_SECONDS",
    "ListeningRedisBackend",
    "Realtime",
    "RealtimeEvent",
    "RealtimeMessage",
    "ResyncSubscriber",
    "announce_after_commit",
    "create_realtime",
    "event_stream",
)
