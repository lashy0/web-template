from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from pak_simulator.errors import ApiError
from pak_simulator.model import Pak, Sessions
from pak_simulator.simulation.state import PakStatus, SlotStatus
from tests.unit.simulation.runner.support import make_run
from tests.unit.support import TEST_TIMEOUT, running_task, wait_until, yield_control

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


async def scheduling_sleep(seconds: float) -> None:
    assert seconds == 0, "No polling delay is needed to wait for queue changes"
    await yield_control(seconds)


@pytest.mark.parametrize("together", [False, True])
async def test_once_processes_every_unit(
    client: AsyncMock,
    pak: Pak,
    sessions: Sessions,
    together: bool,
) -> None:
    run = make_run(pak, replace(sessions, together=together), client)

    result = await run.run()

    assert result.successful and result.completed_attempts == len(pak.dev_euis)


async def test_synchronized_loading_waits_for_every_slot(
    client: AsyncMock,
    pak: Pak,
    sessions: Sessions,
) -> None:
    pak = replace(pak, dev_euis=tuple(f"{no:016X}" for no in range(1, 7)))
    completed = {session_id: asyncio.Event() for session_id in ("session-1", "session-2")}
    release = asyncio.Event()

    async def complete_session(session_id: str, result: str) -> None:
        if result != "aborted" and session_id in completed:
            completed[session_id].set()

            if session_id == "session-2":
                await release.wait()

    client.complete_session.side_effect = complete_session
    run = make_run(pak, replace(sessions, together=True), client)

    async with running_task(run.run()) as task:
        await asyncio.wait_for(asyncio.gather(*(event.wait() for event in completed.values())), TEST_TIMEOUT)
        await wait_until(lambda: run.snapshot().slots[0].status is SlotStatus.PASSED)
        assert client.open_session.await_count == pak.slots
        assert not task.done()
        release.set()
        result = await asyncio.wait_for(task, TEST_TIMEOUT)

    assert result.successful and result.completed_attempts == 6
    assert client.open_session.await_count == 6


async def test_failed_checks_do_not_fail_simulator(
    client: AsyncMock,
    pak: Pak,
    sessions: Sessions,
) -> None:
    pak = replace(pak, profile=replace(pak.profile, pass_rate=0))
    run = make_run(pak, sessions, client)

    result = await run.run()

    assert result.successful and result.failed_attempts == 2


@pytest.mark.parametrize("together", [False, True])
async def test_retests_respect_maximum_attempts(
    client: AsyncMock,
    pak: Pak,
    sessions: Sessions,
    together: bool,
) -> None:
    pak = replace(pak, profile=replace(pak.profile, pass_rate=0))
    sessions = replace(sessions, together=together, retest=replace(sessions.retest, chance=1, max_attempts=3))
    run = make_run(pak, sessions, client)

    result = await run.run()

    stats = run.snapshot().stats
    assert (result.completed_attempts, result.failed_attempts, result.processed_units) == (6, 6, 2)
    assert (stats.failed, stats.attempts_processed, stats.actual_pass_rate) == (6, 6, 0)
    assert result.unfinished_units == 0


async def test_retest_moves_to_other_slot(client: AsyncMock, pak: Pak, sessions: Sessions) -> None:
    pak = replace(pak, dev_euis=pak.dev_euis[:1], profile=replace(pak.profile, pass_rate=0))
    sessions = replace(sessions, retest=replace(sessions.retest, chance=1, other_slot=1, max_attempts=2))
    run = make_run(pak, sessions, client, sleep=scheduling_sleep)

    result = await asyncio.wait_for(run.run(), TEST_TIMEOUT)

    attempts = client.open_session.await_args_list
    assert result.successful and result.processed_units == 1
    assert len(attempts) == 2
    assert attempts[0].kwargs["slot_no"] != attempts[1].kwargs["slot_no"]


@pytest.mark.parametrize("stop", ["cancel", "access"])
async def test_idle_slot_stops_with_busy_sibling(
    client: AsyncMock,
    pak: Pak,
    sessions: Sessions,
    stop: str,
) -> None:
    pak = replace(pak, dev_euis=pak.dev_euis[:1])
    sessions = replace(sessions, retest=replace(sessions.retest, chance=1, max_attempts=2))
    busy = asyncio.Event()
    release = asyncio.Event()

    async def complete_step(_session_id: str, **_kwargs: Any) -> None:
        busy.set()
        await release.wait()
        raise ApiError(403, None, "Access denied")

    client.complete_step.side_effect = complete_step
    run = make_run(pak, sessions, client, sleep=scheduling_sleep)

    async with running_task(run.run()) as task:
        await asyncio.wait_for(busy.wait(), TEST_TIMEOUT)
        await asyncio.sleep(0)
        assert run.running_units == 1 and not task.done()

        if stop == "cancel":
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, TEST_TIMEOUT)

            result = run.result
        else:
            release.set()
            result = await asyncio.wait_for(task, TEST_TIMEOUT)

    assert result.status is (PakStatus.STOPPED if stop == "cancel" else PakStatus.ERROR)
    assert result.unfinished_units == 1 and result.processed_units == 0
    client.complete_session.assert_awaited_once_with("session-1", "aborted")
