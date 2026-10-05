"""Refresh the terminal in the simulation's event loop."""

from __future__ import annotations

import asyncio

from rich.console import Console, RenderableType
from rich.live import Live

from pak_simulator.application import SimulationExecution
from pak_simulator.simulation.state import EventLog, RunResult
from pak_simulator.terminal import dashboard


async def run_live(
    execution: SimulationExecution,
    events: EventLog,
    *,
    console: Console,
    speed: float
) -> tuple[RunResult, ...]:
    """Render consistent snapshots without reading runtime state from a thread."""

    def frame() -> RenderableType:
        # No await between copies: simulation tasks cannot mutate either source.
        return dashboard.render(execution.snapshots, events.snapshot(), speed=speed)

    with Live(frame(), console=console, auto_refresh=False, transient=False) as display:

        async def refresh() -> None:
            while True:
                await asyncio.sleep(0.25)
                display.update(frame(), refresh=True)

        async with asyncio.TaskGroup() as group:
            refresh_task = group.create_task(refresh())

            try:
                return await execution.execute()
            finally:
                refresh_task.cancel()
                display.update(frame(), refresh=True)
