from __future__ import annotations

import asyncio
from datetime import datetime
from io import StringIO
from threading import get_ident
from unittest.mock import AsyncMock

import pytest
from rich.console import Console

from pak_simulator.application import open_simulation_run
from pak_simulator.contracts import ClientFactory
from pak_simulator.model import Pak, Sessions, Simulation
from pak_simulator.simulation.state import Event, EventLog
from pak_simulator.terminal.live import run_live
from tests.unit.support import TEST_TIMEOUT, block_calls, running_task

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


class RecordingOutput(StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.threads: set[int] = set()
        self.updated = asyncio.Event()

    def write(self, text: str) -> int:
        self.threads.add(get_ident())
        written = super().write(text)
        if "Event 19" in self.getvalue():
            self.updated.set()
        return written


async def test_live_refresh_and_simulation_share_one_thread(
    pak: Pak, sessions: Sessions, client: AsyncMock, client_factory: ClientFactory
) -> None:
    output = RecordingOutput()
    console = Console(file=output, force_terminal=True, width=160, height=100, _environ={"TERM": "xterm"})
    events = EventLog()
    step_started, release_results = block_calls(client.complete_step)
    simulation = Simulation("http://backend", True, sessions, (pak,), (pak.profile,))

    async with open_simulation_run(
        simulation, events, speed=1, loop=False, seed=4, client_factory=client_factory
    ) as execution:
        async with running_task(run_live(execution, events, console=console, speed=1)) as task:
            await asyncio.wait_for(step_started.wait(), TEST_TIMEOUT)
            for number in range(20):
                events.add(Event(datetime.now(), pak.code, None, f"Event {number}", "info"))
                await asyncio.sleep(0)
            await asyncio.wait_for(output.updated.wait(), TEST_TIMEOUT)
            assert "Event 19" in output.getvalue()
            assert not task.done()
            release_results.set()
            results = await asyncio.wait_for(task, TEST_TIMEOUT)

    assert all(result.successful for result in results)
    assert output.threads == {get_ident()}
    assert "Finished" in output.getvalue()


async def test_live_cancellation_finishes_sessions_and_stops_refresh(
    pak: Pak, sessions: Sessions, client: AsyncMock, client_factory: ClientFactory
) -> None:
    output = RecordingOutput()
    events = EventLog()
    step_started, _release_results = block_calls(client.complete_step)
    simulation = Simulation("http://backend", True, sessions, (pak,), (pak.profile,))

    async with open_simulation_run(
        simulation, events, speed=1, loop=False, seed=4, client_factory=client_factory
    ) as execution:
        async with running_task(run_live(execution, events, console=Console(file=output), speed=1)) as task:
            await asyncio.wait_for(step_started.wait(), TEST_TIMEOUT)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, TEST_TIMEOUT)

    assert client.open_session.await_count > 0
    assert client.complete_session.await_count == client.open_session.await_count
    assert all(request.args[1] == "aborted" for request in client.complete_session.await_args_list)
    assert "Stopped" in output.getvalue()


def test_event_snapshot_survives_replacement_and_log_overflow() -> None:
    events = EventLog(size=1)
    first = Event(datetime.now(), "PAK", None, "First", "info", topic="progress")
    events.add(first)
    snapshot = events.snapshot()
    events.add(Event(datetime.now(), "PAK", None, "Replacement", "info", topic="progress"))
    events.add(Event(datetime.now(), "PAK", None, "Another", "info"))

    assert snapshot.recent == (first,)
    assert snapshot.limit == 1
    assert events.snapshot().recent[0].text == "Another"
