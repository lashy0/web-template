from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any
from unittest.mock import AsyncMock, call

import pytest

from pak_simulator.errors import ApiError
from pak_simulator.model import Pak, Sessions
from pak_simulator.simulation.state import PakStatus, SlotStatus
from tests.unit.simulation.runner.support import make_run
from tests.unit.support import TEST_TIMEOUT

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


@pytest.mark.parametrize("together", [False, True])
async def test_api_errors_fail_run(client: AsyncMock, pak: Pak, sessions: Sessions, together: bool) -> None:
    client.open_session.side_effect = ApiError(500, None, "Intentional failure")
    run = make_run(pak, replace(sessions, together=together), client)

    result = await run.run()

    stats = run.snapshot().stats
    assert (result.status, result.execution_errors, result.unfinished_units) == (PakStatus.ERROR, 2, 2)
    assert (stats.errors, stats.cleanup_errors, stats.attempts_processed) == (2, 0, 2)


async def test_access_error_keeps_unfinished_units(client: AsyncMock, pak: Pak, sessions: Sessions) -> None:
    client.open_session.side_effect = ApiError(403, None, "Access denied")
    run = make_run(pak, sessions, client)

    result = await run.run()

    assert result.unfinished_units == 2 and result.processed_units == 0


@pytest.mark.parametrize("together", [False, True])
@pytest.mark.parametrize("failure", ["access", "internal"])
async def test_slot_failure_aborts_its_sibling_with_the_correct_reason(
    client: AsyncMock,
    pak: Pak,
    sessions: Sessions,
    together: bool,
    failure: str,
) -> None:
    sibling_waiting = asyncio.Event()

    async def complete_step(session_id: str, **_kwargs: Any) -> None:
        if session_id == "session-1":
            await sibling_waiting.wait()

            if failure == "access":
                raise ApiError(403, None, "Access denied")

            raise RuntimeError("Internal failure in the first slot")

        sibling_waiting.set()
        await asyncio.Event().wait()

    client.complete_step.side_effect = complete_step
    run = make_run(pak, replace(sessions, together=together), client)
    result = await asyncio.wait_for(run.run(), TEST_TIMEOUT)

    assert result.status is PakStatus.ERROR and result.execution_errors == 1
    assert result.unfinished_units == len(pak.dev_euis)
    assert client.open_session.await_count == pak.slots
    client.complete_session.assert_has_awaits(
        [call("session-1", "aborted"), call("session-2", "aborted")], any_order=True
    )
    assert client.complete_session.await_count == pak.slots
    assert run.snapshot().slots[1].status is SlotStatus.ABORTED

    if failure == "access":
        assert run.snapshot().slots[1].note == "PAK stopped after an access error"
        assert run.snapshot().stats.errors == 1 and run.snapshot().stats.internal_errors == 0
    else:
        assert run.snapshot().slots[1].note == "PAK stopped after an internal simulator error"
        assert run.snapshot().stats.errors == 0 and run.snapshot().stats.internal_errors == 1


async def test_cleanup_failure_fails_run(client: AsyncMock, pak: Pak, sessions: Sessions) -> None:
    client.complete_session.side_effect = ApiError(500, None, "Intentional cleanup failure")
    sessions = replace(sessions, abandon=1)
    run = make_run(pak, sessions, client)

    result = await run.run()

    stats = run.snapshot().stats
    assert not result.successful and result.execution_errors == 2
    assert (stats.abandoned, stats.errors, stats.cleanup_errors, stats.attempts_processed) == (2, 0, 2, 2)


async def test_unavailable_unit_is_skipped(client: AsyncMock, pak: Pak, sessions: Sessions) -> None:
    client.open_session.side_effect = ApiError(404, "verification_kg_not_found", "Unit not found")
    run = make_run(pak, sessions, client)

    result = await run.run()

    stats = run.snapshot().stats
    assert result.skipped_attempts == 2 and result.execution_errors == 0
    assert (stats.skipped, stats.attempts_processed, stats.completed_attempts) == (2, 2, 0)


@pytest.mark.parametrize("together", [False, True])
async def test_resumed_first_step_conflict_does_not_fail_once_run(
    client: AsyncMock,
    pak: Pak,
    sessions: Sessions,
    together: bool,
) -> None:
    pak = replace(pak, slots=1, dev_euis=pak.dev_euis[:1])
    client.start_step.side_effect = [
        ApiError(409, "verification_step_already_exists", "Conflicting first step"),
        *([None] * len(pak.profile.checks)),
    ]
    run = make_run(pak, replace(sessions, together=together), client)

    result = await run.run()

    assert result.successful
    assert result.completed_attempts == result.processed_units == 1
    assert result.execution_errors == result.unfinished_units == 0
    assert client.complete_session.await_args_list == [call("session-1", "aborted"), call("session-2", "passed")]
