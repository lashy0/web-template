from __future__ import annotations

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, call

import pytest

from pak_simulator.application import open_simulation_run
from pak_simulator.contracts import ClientFactory
from pak_simulator.model import Simulation
from pak_simulator.simulation.state import Event, EventLog, EventSinkError, PakStatus, SlotStatus
from tests.unit.support import TEST_TIMEOUT, block_calls, running_task, wait_until

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


@pytest.mark.parametrize("together", [False, True])
@pytest.mark.parametrize("action", ["complete_step", "abort"])
async def test_internal_pak_failure_does_not_cancel_other_paks(
    paired_simulation: Simulation,
    paired_clients: dict[str, AsyncMock],
    paired_factory: ClientFactory,
    caplog: pytest.LogCaptureFixture,
    together: bool,
    action: str,
) -> None:
    broken, healthy = paired_clients["client"], paired_clients["other"]
    getattr(broken, "complete_step" if action == "complete_step" else "complete_session").side_effect = RuntimeError(
        f"Intentional internal failure during {action}"
    )
    step_started, release_results = block_calls(healthy.complete_step)
    sessions = replace(paired_simulation.sessions, together=together, abandon=1 if action == "abort" else 0)
    simulation = replace(paired_simulation, sessions=sessions)
    events = EventLog()

    async with open_simulation_run(
        simulation, events, speed=100, loop=False, seed=4, client_factory=paired_factory
    ) as execution:
        async with running_task(execution.execute()) as task:
            await asyncio.wait_for(step_started.wait(), TEST_TIMEOUT)
            await wait_until(lambda: execution.snapshots[0].stats.internal_errors > 0)
            broken_snapshot, healthy_snapshot = execution.snapshots
            assert broken_snapshot.status is PakStatus.ERROR
            assert broken_snapshot.running_units == 0
            assert all(slot.status is not SlotStatus.RUNNING for slot in broken_snapshot.slots)
            assert healthy_snapshot.status is PakStatus.RUNNING and not task.done()
            assert any(event.pak == "PAK" and event.level == "error" for event in events.snapshot().recent)
            release_results.set()
            results = await asyncio.wait_for(task, TEST_TIMEOUT)

    assert not results[0].successful and results[0].execution_errors == 1
    assert results[1].successful

    for client in paired_clients.values():
        client.aclose.assert_awaited_once()
        assert client.method_calls[-1] == call.aclose()

    assert broken_snapshot.stats.internal_errors == 1
    assert broken_snapshot.stats.errors == 0 and broken_snapshot.stats.cleanup_errors == 0
    assert "Intentional internal failure" in caplog.text and "Traceback" in caplog.text

    if action == "complete_step":
        assert results[0].unfinished_units == len(simulation.paks[0].dev_euis)
        assert broken_snapshot.stats.attempts_processed == 0
        assert broken.complete_session.await_count == broken.open_session.await_count > 0
        assert all(request.args[1] == "aborted" for request in broken.complete_session.await_args_list)


async def test_healthy_pak_keeps_looping_after_other_pak_crashes(
    paired_simulation: Simulation,
    paired_clients: dict[str, AsyncMock],
    paired_factory: ClientFactory,
) -> None:
    paired_clients["client"].complete_step.side_effect = RuntimeError("Intentional internal failure")
    healthy = paired_clients["other"]
    step_started, release_results = block_calls(healthy.complete_step)
    async with open_simulation_run(
        paired_simulation, EventLog(), speed=100, loop=True, seed=4, client_factory=paired_factory
    ) as execution:
        async with running_task(execution.execute()) as task:
            await asyncio.wait_for(step_started.wait(), TEST_TIMEOUT)
            await wait_until(lambda: execution.snapshots[0].stats.internal_errors > 0)
            release_results.set()
            await wait_until(
                lambda: execution.snapshots[1].stats.completed_attempts > len(paired_simulation.paks[1].dev_euis)
            )
            assert not task.done() and execution.snapshots[0].status is PakStatus.ERROR
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, TEST_TIMEOUT)

        assert execution.snapshots[1].status is PakStatus.STOPPED

    assert healthy.complete_session.await_count == healthy.open_session.await_count
    assert {request.args[0] for request in healthy.complete_session.await_args_list} == {
        f"session-{number}" for number in range(1, healthy.open_session.await_count + 1)
    }


async def test_shared_event_output_failure_stops_whole_run(
    paired_simulation: Simulation,
    paired_clients: dict[str, AsyncMock],
    paired_factory: ClientFactory,
) -> None:
    calls = 0

    def sink(_event: Event) -> None:
        nonlocal calls
        calls += 1

        if calls == 1:
            raise RuntimeError("Terminal output failed")

    async with open_simulation_run(
        paired_simulation, EventLog(sink=sink), speed=100, loop=False, seed=4, client_factory=paired_factory
    ) as execution:
        with pytest.raises(ExceptionGroup) as exc_info:
            await asyncio.wait_for(execution.execute(), TEST_TIMEOUT)

        assert exc_info.value.subgroup(EventSinkError) is not None
        assert all(snapshot.stats.internal_errors == 0 for snapshot in execution.snapshots)

    for client in paired_clients.values():
        client.aclose.assert_awaited_once()
        assert client.method_calls[-1] == call.aclose()
        assert client.complete_session.await_count == client.open_session.await_count
        assert {request.args[0] for request in client.complete_session.await_args_list} == {
            f"session-{number}" for number in range(1, client.open_session.await_count + 1)
        }
