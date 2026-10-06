"""Event delivery inside one process, and the stream a browser reads."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, ClassVar

import msgspec
import pytest

from app.config import get_settings
from app.lib.realtime import RESYNC, Realtime, RealtimeEvent, RealtimeMessage, create_realtime, event_stream

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

pytestmark = [pytest.mark.anyio, pytest.mark.unit]

CAN_READ = frozenset({"things.read"})


class ThingChanged(RealtimeEvent):
    event_type: ClassVar[str] = "thing.changed"
    permission: ClassVar[str] = "things.read"

    thing_id: int


@pytest.fixture
async def realtime() -> AsyncGenerator[Realtime]:
    """The delivery of one process, kept in memory as the test settings say."""
    realtime = create_realtime(get_settings())
    await realtime.start()

    yield realtime

    await realtime.close()


async def test_published_event_reaches_a_subscriber_with_its_permission(realtime: Realtime) -> None:
    async with realtime.subscribe(CAN_READ) as subscriber:
        await realtime.publish(ThingChanged(thing_id=7))
        payload = await subscriber.get()

    assert payload == msgspec.json.encode(RealtimeMessage(type="thing.changed", data=msgspec.Raw(b'{"thingId":7}')))


async def test_subscriber_far_behind_is_told_to_resync(realtime: Realtime) -> None:
    async with realtime.subscribe(CAN_READ) as subscriber:
        await asyncio.gather(*(realtime.publish(ThingChanged(thing_id=number)) for number in range(300)))
        payload = await subscriber.get()

    assert payload == msgspec.json.encode(RESYNC)


async def test_event_stream_opens_with_a_resync(realtime: Realtime) -> None:
    stream = event_stream(realtime, CAN_READ)

    first = await anext(stream)
    await stream.aclose()

    assert first.encode() == b"event: resync\r\ndata: {}\r\n\r\n"


async def test_event_stream_carries_events_the_user_may_receive(realtime: Realtime) -> None:
    stream = event_stream(realtime, CAN_READ)
    await anext(stream)

    await realtime.publish(ThingChanged(thing_id=7))
    message = await anext(stream)
    await stream.aclose()

    assert message.encode() == b'event: thing.changed\r\ndata: {"thingId":7}\r\n\r\n'


async def test_event_stream_withholds_events_the_user_may_not_receive(realtime: Realtime) -> None:
    stream = event_stream(realtime, frozenset(), heartbeat=0.05)
    await anext(stream)

    await realtime.publish(ThingChanged(thing_id=7))
    message = await anext(stream)
    await stream.aclose()

    assert message.encode() == b": ping\r\n\r\n"


async def test_event_stream_skips_a_malformed_message(realtime: Realtime) -> None:
    stream = event_stream(realtime, CAN_READ)
    await anext(stream)

    await realtime.channels.wait_published(b"not an event", realtime.channel("things.read"))  # pyright: ignore[reportUnknownMemberType]
    await realtime.publish(ThingChanged(thing_id=7))
    message = await anext(stream)
    await stream.aclose()

    assert message.encode() == b'event: thing.changed\r\ndata: {"thingId":7}\r\n\r\n'


async def test_event_stream_ends_after_its_lifetime(realtime: Realtime) -> None:
    stream = event_stream(realtime, CAN_READ, heartbeat=0.05, lifetime=0.1)

    messages = [message.encode() async for message in stream]

    assert messages[0].startswith(b"event: resync") and set(messages[1:]) == {b": ping\r\n\r\n"}
