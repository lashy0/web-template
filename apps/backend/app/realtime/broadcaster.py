import asyncio

from app.realtime.events import RealtimeEvent, format_sse_event


class EventBroadcaster:
    """Keeps one bounded queue per connected SSE client."""

    def __init__(self) -> None:
        self._clients: set[asyncio.Queue[str]] = set()

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._clients.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._clients.discard(queue)

    def broadcast(self, event: RealtimeEvent) -> None:
        serialized_event = format_sse_event(event)

        for queue in tuple(self._clients):
            if queue.full():
                self._clients.discard(queue)
                continue

            queue.put_nowait(serialized_event)
