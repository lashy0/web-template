"""Small helpers for HTTP clients and bounded background tasks in tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine
from contextlib import asynccontextmanager, suppress
from typing import Any
from unittest.mock import AsyncMock, Mock

import httpx2

from pak_simulator.client import PakClient
from pak_simulator.contracts import ClientFactory, SessionResponse, VerificationClient

TEST_TIMEOUT = 5
HttpHandler = (
    Callable[[httpx2.Request], httpx2.Response]
    | Callable[[httpx2.Request], Coroutine[None, None, httpx2.Response]]
)


async def yield_control(_seconds: float) -> None:
    await asyncio.sleep(0)


def make_client() -> AsyncMock:
    """Mock the client interface without implementing backend session rules."""
    client = AsyncMock(spec_set=VerificationClient)

    async def open_session(
        *,
        dev_eui: str,
        slot_no: int,
        firmware_version: str,
        total_steps: int,
    ) -> SessionResponse:
        return SessionResponse(
            id=f"session-{client.open_session.await_count}",
            firmware_version=firmware_version,
            total_steps=total_steps,
        )

    client.open_session.side_effect = open_session

    return client


def make_client_factory(client: VerificationClient) -> Mock:
    return Mock(spec=ClientFactory, return_value=client)


def block_calls(method: AsyncMock) -> tuple[asyncio.Event, asyncio.Event]:
    """Pause an async mock until the test releases it."""
    started, release = asyncio.Event(), asyncio.Event()

    async def wait(*_args: Any, **_kwargs: Any) -> None:
        started.set()
        await release.wait()

    method.side_effect = wait

    return started, release


@asynccontextmanager
async def mock_client(
    handler: HttpHandler,
    *,
    retry_delays: tuple[float, ...] | None = None,
    sleep: Callable[[float], Awaitable[None]] = yield_control,
) -> AsyncIterator[PakClient]:
    options = {} if retry_delays is None else {"retry_delays": retry_delays}
    client = PakClient(
        server="http://backend",
        client_id="client",
        access_key="secret",
        verify=True,
        transport=httpx2.MockTransport(handler),
        sleep=sleep,
        **options,
    )
    try:
        yield client
    finally:
        await client.aclose()


@asynccontextmanager
async def running_task[T](coroutine: Coroutine[Any, Any, T]) -> AsyncIterator[asyncio.Task[T]]:
    task = asyncio.create_task(coroutine)

    try:
        yield task
    finally:
        if not task.done():
            task.cancel()

            with suppress(asyncio.CancelledError):
                await asyncio.wait_for(task, TEST_TIMEOUT)
        elif not task.cancelled():
            # Retrieve a failure even if the test failed before awaiting the task.
            task.exception()


async def wait_until(predicate: Callable[[], bool]) -> None:
    async with asyncio.timeout(TEST_TIMEOUT):
        while not predicate():
            await asyncio.sleep(0)
