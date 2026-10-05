from __future__ import annotations

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, call

import pytest

from pak_simulator.application import open_simulation_run
from pak_simulator.contracts import ClientFactory, VerificationClient
from pak_simulator.model import Pak, Sessions, Simulation
from pak_simulator.simulation.state import EventLog, PakStatus
from tests.unit.application.support import make_simulation
from tests.unit.support import TEST_TIMEOUT, block_calls, running_task, wait_until

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


async def test_execution_returns_results_and_closes_clients(
    client: AsyncMock,
    client_factory: ClientFactory,
    pak: Pak,
    sessions: Sessions,
) -> None:
    async with open_simulation_run(
        make_simulation(pak, sessions),
        EventLog(),
        speed=1,
        loop=False,
        seed=4,
        client_factory=client_factory,
    ) as execution:
        assert len(execution.snapshots) == 1
        results = await execution.execute()
        client.aclose.assert_not_awaited()

    assert len(results) == 1 and results[0].successful
    assert results[0].completed_attempts == len(pak.dev_euis)
    client.aclose.assert_awaited_once()
    assert client.method_calls[-1] == call.aclose()


async def test_partial_client_creation_closes_clients_already_opened(
    client: AsyncMock,
    pak: Pak,
    sessions: Sessions,
) -> None:
    second_pak = replace(pak, code="PAK-2", client_id="second")
    simulation = replace(make_simulation(pak, sessions), paks=(pak, second_pak))

    def factory(*, server: str, client_id: str, access_key: str, verify: bool) -> VerificationClient:
        if client_id == "second":
            raise RuntimeError("second client could not be created")

        return client

    with pytest.raises(RuntimeError, match="second client"):
        async with open_simulation_run(
            simulation,
            EventLog(),
            speed=1,
            loop=False,
            seed=4,
            client_factory=factory,
        ):
            pytest.fail("a partially constructed run must not be yielded")

    client.aclose.assert_awaited_once()
    client.open_session.assert_not_awaited()


async def test_cancellation_aborts_open_sessions_before_closing_clients(
    client: AsyncMock,
    client_factory: ClientFactory,
    pak: Pak,
    sessions: Sessions,
) -> None:
    step_started, _release = block_calls(client.complete_step)

    async with open_simulation_run(
        make_simulation(pak, sessions),
        EventLog(),
        speed=1,
        loop=False,
        seed=4,
        client_factory=client_factory,
    ) as execution:
        async with running_task(execution.execute()) as task:
            await asyncio.wait_for(step_started.wait(), TEST_TIMEOUT)
            await wait_until(lambda: client.open_session.await_count == pak.slots)
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, TEST_TIMEOUT)

            client.aclose.assert_not_awaited()
            assert client.complete_session.await_count == pak.slots

    assert client.open_session.await_count == pak.slots
    client.complete_session.assert_has_awaits(
        [call(f"session-{number}", "aborted") for number in range(1, pak.slots + 1)], any_order=True
    )
    client.aclose.assert_awaited_once()
    assert client.method_calls[-1] == call.aclose()


async def test_cancellation_stops_all_paks_even_if_cleanup_crashes(
    paired_simulation: Simulation,
    paired_clients: dict[str, AsyncMock],
    paired_factory: ClientFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    started = [block_calls(client.complete_step)[0] for client in paired_clients.values()]
    paired_clients["client"].complete_session.side_effect = RuntimeError("Intentional internal failure during abort")

    async with open_simulation_run(
        paired_simulation, EventLog(), speed=100, loop=False, seed=4, client_factory=paired_factory
    ) as execution:
        async with running_task(execution.execute()) as task:
            await asyncio.wait_for(asyncio.gather(*(event.wait() for event in started)), TEST_TIMEOUT)
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, TEST_TIMEOUT)

            assert all(snapshot.status is PakStatus.STOPPED for snapshot in execution.snapshots)

    for client in paired_clients.values():
        client.aclose.assert_awaited_once()
        assert client.method_calls[-1] == call.aclose()

    healthy = paired_clients["other"]
    assert healthy.complete_session.await_count == healthy.open_session.await_count
    assert all(request.args[1] == "aborted" for request in healthy.complete_session.await_args_list)
    assert "Intentional internal failure during abort" in caplog.text
