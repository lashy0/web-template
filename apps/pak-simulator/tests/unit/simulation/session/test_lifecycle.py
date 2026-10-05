from __future__ import annotations

import asyncio
import random
from dataclasses import replace
from unittest.mock import AsyncMock, call

import pytest

from pak_simulator.errors import ApiError
from pak_simulator.model import Pak, Sessions
from pak_simulator.simulation.session import SessionExecutor
from pak_simulator.simulation.state import AttemptOutcome, SlotState, Unit
from tests.unit.simulation.session.support import make_executor
from tests.unit.support import TEST_TIMEOUT, running_task

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


async def test_close_aborts_only_current_session(abandoning_executor: SessionExecutor, client: AsyncMock) -> None:
    slot = SlotState(1)
    await abandoning_executor.execute(slot, Unit("0000000000000001"), random.Random(1))
    await abandoning_executor.execute(slot, Unit("0000000000000002"), random.Random(1))
    await abandoning_executor.execute(slot, Unit("0000000000000003"), random.Random(1))
    assert abandoning_executor.open_sessions == 1
    client.complete_session.assert_not_awaited()

    await abandoning_executor.close()

    assert abandoning_executor.open_sessions == 0
    client.complete_session.assert_awaited_once_with("session-3", "aborted")


async def test_close_waits_for_other_sessions_when_one_abort_crashes(
    client: AsyncMock,
    abandoning_executor: SessionExecutor,
) -> None:
    second_abort_started = asyncio.Event()
    release_second_abort = asyncio.Event()
    finished: list[str] = []

    async def complete_session(session_id: str, result: str) -> None:
        assert result == "aborted"

        if session_id == "session-1":
            raise RuntimeError("First session abort crashed")

        second_abort_started.set()
        await release_second_abort.wait()
        finished.append(session_id)

    client.complete_session.side_effect = complete_session

    for slot_no in (1, 2):
        await abandoning_executor.execute(SlotState(slot_no), Unit(f"{slot_no:016X}"), random.Random(1))

    async with running_task(abandoning_executor.close()) as task:
        await asyncio.wait_for(second_abort_started.wait(), TEST_TIMEOUT)
        assert not task.done()
        release_second_abort.set()

        with pytest.raises(ExceptionGroup, match="Session cleanup failed"):
            await asyncio.wait_for(task, TEST_TIMEOUT)

    client.complete_session.assert_has_awaits(
        [call("session-1", "aborted"), call("session-2", "aborted")], any_order=True
    )
    assert finished == ["session-2"]


async def test_step_failure_aborts_session(abandoning_executor: SessionExecutor, client: AsyncMock) -> None:
    client.complete_step.side_effect = ApiError(500, None, "Intentional failure")

    with pytest.raises(ApiError):
        await abandoning_executor.execute(SlotState(1), Unit("0000000000000001"), random.Random(1))

    assert abandoning_executor.open_sessions == 0
    client.complete_session.assert_awaited_once_with("session-1", "aborted")


async def test_failed_critical_check_stops_later_steps(client: AsyncMock, pak: Pak, sessions: Sessions) -> None:
    checks = (replace(pak.profile.checks[0], critical=True, low=2, high=3), *pak.profile.checks[1:])
    profile = replace(pak.profile, pass_rate=None, checks=checks)
    executor = make_executor(client, profile, sessions)

    outcome = await executor.execute(SlotState(1), Unit("0000000000000001"), random.Random(1))

    assert outcome is AttemptOutcome.FAILED
    assert client.start_step.await_count == client.complete_step.await_count == 1
    client.complete_session.assert_awaited_once_with("session-1", "failed")
