import random
from unittest.mock import AsyncMock, call

import pytest

from pak_simulator.contracts import SessionResponse
from pak_simulator.model import Pak
from pak_simulator.simulation.session import SessionExecutor
from pak_simulator.simulation.state import AttemptOutcome, SlotState, Unit

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


async def test_reused_partial_session_is_restarted(
    abandoning_executor: SessionExecutor,
    client: AsyncMock
) -> None:
    client.open_session.side_effect = [
        SessionResponse(id="old", firmware_version="1", total_steps=3, completed_steps=1),
        SessionResponse(id="new", firmware_version="1", total_steps=3),
    ]

    await abandoning_executor.execute(SlotState(1), Unit("0000000000000001"), random.Random(1))

    assert client.open_session.await_count == 2
    client.complete_session.assert_awaited_once_with("old", "aborted")
    assert all(request.args[0] == "new" for request in client.start_step.await_args_list)
    assert abandoning_executor.open_sessions == 1


@pytest.mark.parametrize("firmware, total_steps, restarted", [("1", 3, False), ("old", 3, True), ("1", 1, True)])
async def test_empty_session_reused_only_with_compatible_parameters(
    client: AsyncMock,
    pak: Pak,
    executor: SessionExecutor,
    firmware: str,
    total_steps: int,
    restarted: bool,
) -> None:
    client.open_session.side_effect = [
        SessionResponse(id="old", firmware_version=firmware, total_steps=total_steps),
        SessionResponse(id="new", firmware_version=pak.profile.firmware_version, total_steps=len(pak.profile.checks)),
    ]

    outcome = await executor.execute(SlotState(1), Unit(pak.dev_euis[0]), random.Random(1))

    assert outcome is AttemptOutcome.PASSED
    assert executor.open_sessions == 0
    assert client.open_session.await_count == (2 if restarted else 1)
    client.open_session.assert_has_awaits(
        [
            call(
                dev_eui=pak.dev_euis[0],
                slot_no=1,
                firmware_version=pak.profile.firmware_version,
                total_steps=len(pak.profile.checks),
            )
        ]
        * (2 if restarted else 1)
    )
    current = "new" if restarted else "old"
    expected = [call("old", "aborted"), call("new", "passed")] if restarted else [call("old", "passed")]
    assert client.complete_session.await_args_list == expected
    assert client.start_step.await_count == client.complete_step.await_count == len(pak.profile.checks)
    assert all(request.args[0] == current for request in client.start_step.await_args_list)
    assert all(request.args[0] == current for request in client.complete_step.await_args_list)
