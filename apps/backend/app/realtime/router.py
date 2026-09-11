import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.realtime.broadcaster import EventBroadcaster

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    broadcaster: EventBroadcaster = request.app.state.broadcaster
    queue = broadcaster.subscribe()

    async def event_stream() -> AsyncGenerator[str]:
        try:
            while not await request.is_disconnected():
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=15)

                except TimeoutError:
                    yield ": keepalive\n\n"

        finally:
            broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
