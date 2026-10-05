from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from pak_simulator.contracts import SessionResponse
from pak_simulator.model import Pak, Sessions
from pak_simulator.simulation.runner import PakRun
from pak_simulator.simulation.state import EventLog, PakStatus, SlotState, SlotStatus, Unit
from pak_simulator.values import Span
from tests.unit.simulation.runner.support import make_run
from tests.unit.support import TEST_TIMEOUT, make_client

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds

    async def sleep(self, seconds: float) -> None:
        self.advance(seconds)
        await asyncio.sleep(0)


async def test_seed_outcomes_ignore_response_order(pak: Pak, sessions: Sessions) -> None:
    check = replace(pak.profile.checks[0], value=Span(1, 100), low=40, high=60)
    pak = replace(pak, profile=replace(pak.profile, checks=(check, check, check), pass_rate=0.5))
    sessions = replace(sessions, abandon=0.5)

    async def execute(
        first_slot: int,
    ) -> tuple[list[int], list[dict[str, object]], list[tuple[str | None, SlotStatus]]]:
        client = make_client()
        opened = {slot: asyncio.Event() for slot in (1, 2)}
        first_result = asyncio.Event()
        response_order: list[int] = []

        async def open_session(
            *,
            dev_eui: str,
            slot_no: int,
            firmware_version: str,
            total_steps: int
        ) -> SessionResponse:
            opened[slot_no].set()
            await opened[3 - slot_no].wait()

            if slot_no != first_slot:
                await first_result.wait()

            response_order.append(slot_no)

            return SessionResponse(id=dev_eui, firmware_version=firmware_version, total_steps=total_steps)

        async def complete_step(session_id: str, *, step_no: int, **_kwargs: Any) -> None:
            if session_id == pak.dev_euis[first_slot - 1] and step_no == 1:
                first_result.set()

        client.open_session.side_effect = open_session
        client.complete_step.side_effect = complete_step
        run = make_run(pak, sessions, client)
        result = await asyncio.wait_for(run.run(), TEST_TIMEOUT)
        assert result.successful and result.processed_units == len(pak.dev_euis)
        steps = [
            {"devEui": request.args[0], **request.kwargs}
            for request in sorted(
                client.complete_step.await_args_list, key=lambda request: (request.args[0], request.kwargs["step_no"])
            )
        ]
        outcomes = sorted(
            [(slot.dev_eui, slot.status) for slot in run.snapshot().slots], key=lambda item: item[0] or ""
        )

        return response_order, steps, outcomes

    first_order, first_steps, first_outcomes = await execute(first_slot=1)
    second_order, second_steps, second_outcomes = await execute(first_slot=2)

    assert first_order == [1, 2] and second_order == [2, 1]
    assert first_steps and any(step["value"] != 1 for step in first_steps)
    assert first_steps == second_steps
    assert first_outcomes == second_outcomes


async def test_snapshot_is_independent_of_live_state(client: AsyncMock, pak: Pak, sessions: Sessions) -> None:
    run = make_run(pak, sessions, client)
    snapshot = run.snapshot()

    await run.run()

    assert snapshot.slots[0].outcomes == () and snapshot.status is PakStatus.RUNNING
    assert snapshot.stats.passed == 0 and run.snapshot().stats.passed == 2


async def test_injected_clock_drives_slot_and_load_timing(
    client: AsyncMock,
    pak: Pak,
    sessions: Sessions,
) -> None:
    clock = FakeClock()
    slot = SlotState(1, clock=clock)
    slot.begin(Unit("0000000000000001"), total_steps=1)
    clock.advance(2.5)
    assert slot.elapsed == 2.5
    slot.next_session_at = clock() + 4
    assert slot.next_session_in == 4
    clock.advance(1)
    assert slot.next_session_in == 3
    slot.end(SlotStatus.PASSED)
    clock.advance(3)
    assert slot.elapsed == 3.5

    pak = replace(pak, dev_euis=(*pak.dev_euis, "0000000000000003"))
    sessions = replace(sessions, together=True, swap=Span(10, 10))
    observations: list[tuple[float, float | None, float | None]] = []
    runs: list[PakRun] = []

    async def sleep(seconds: float) -> None:
        if runs and runs[0].next_load_at is not None:
            run = runs[0]
            observations.append((seconds, run.next_load_in, run.snapshot().next_load_in))

        await clock.sleep(seconds)

    run = PakRun(
        pak,
        sessions,
        client,
        speed=2,
        loop=False,
        seed=4,
        events=EventLog(),
        sleep=sleep,
        clock=clock,
    )
    runs.append(run)

    result = await run.run()

    assert result.successful
    assert observations == [(5, 5, 5)]
    assert run.next_load_in is None
