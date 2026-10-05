import asyncio
import random
from typing import Any
from unittest.mock import AsyncMock, call

import pytest

from pak_simulator.errors import ApiError
from pak_simulator.model import Pak
from pak_simulator.simulation.session import SessionExecutor
from pak_simulator.simulation.state import AttemptOutcome, SlotState, Unit
from tests.unit.support import TEST_TIMEOUT

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


@pytest.mark.parametrize("conflict", [False, True])
async def test_started_first_step_reused_or_restarted_when_incompatible(
    executor: SessionExecutor,
    client: AsyncMock,
    pak: Pak,
    conflict: bool,
) -> None:
    client.start_step.side_effect = [
        *([ApiError(409, "verification_step_already_exists", "Conflicting first step")] if conflict else []),
        *([None] * len(pak.profile.checks)),
    ]
    unit = Unit(pak.dev_euis[0])
    slot = SlotState(1)

    outcome = await executor.execute(slot, unit, random.Random(1))

    assert outcome is AttemptOutcome.PASSED
    assert unit.attempt == 1 and slot.outcomes == [True] * len(pak.profile.checks)
    assert executor.open_sessions == 0
    assert client.open_session.await_count == (2 if conflict else 1)
    expected = (
        [call("session-1", "aborted"), call("session-2", "passed")] if conflict else [call("session-1", "passed")]
    )
    assert client.complete_session.await_args_list == expected
    assert client.complete_step.await_count == len(pak.profile.checks)
    first_check = pak.profile.checks[0]
    client.start_step.assert_any_await(
        "session-1",
        step_no=1,
        name=first_check.name,
        label=first_check.label,
        group=first_check.group,
    )


@pytest.mark.parametrize("conflicting_step, expected_sessions", [(1, 2), (2, 1)])
async def test_repeated_or_later_step_conflict_is_not_restarted_indefinitely(
    client: AsyncMock,
    executor: SessionExecutor,
    pak: Pak,
    conflicting_step: int,
    expected_sessions: int,
) -> None:
    async def start_step(_session_id: str, *, step_no: int, **_kwargs: Any) -> None:
        if step_no == conflicting_step:
            raise ApiError(409, "verification_step_already_exists", "Conflicting step")

    client.start_step.side_effect = start_step
    unit = Unit(pak.dev_euis[0])

    async with asyncio.timeout(TEST_TIMEOUT):
        with pytest.raises(ApiError) as exc_info:
            await executor.execute(SlotState(1), unit, random.Random(1))

    assert exc_info.value.status == 409 and exc_info.value.code == "verification_step_already_exists"
    assert unit.attempt == 1 and executor.open_sessions == 0
    assert client.open_session.await_count == expected_sessions
    assert client.complete_session.await_args_list == [
        call(f"session-{number}", "aborted") for number in range(1, expected_sessions + 1)
    ]
    assert client.start_step.await_count == 2
    assert client.complete_step.await_count == conflicting_step - 1
