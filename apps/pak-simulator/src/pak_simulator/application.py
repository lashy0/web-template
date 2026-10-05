"""Application lifecycle for running a configured simulation."""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass

from pak_simulator.client import PakClient
from pak_simulator.contracts import ClientFactory
from pak_simulator.model import Simulation
from pak_simulator.simulation.runner import PakRun
from pak_simulator.simulation.state import EventLog, PakSnapshot, RunResult


@dataclass(slots=True)
class SimulationExecution:
    """A prepared simulation that can be executed once and observed while it runs."""

    _runs: tuple[PakRun, ...]
    _started: bool = False

    @property
    def snapshots(self) -> tuple[PakSnapshot, ...]:
        """Current immutable view of every PAK run."""
        return tuple(run.snapshot() for run in self._runs)

    async def execute(self) -> tuple[RunResult, ...]:
        """Run every PAK concurrently and return its final result."""
        if self._started:
            raise RuntimeError("A simulation execution can only be started once")
        self._started = True

        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(run.run()) for run in self._runs]

        return tuple(task.result() for task in tasks)


@asynccontextmanager
async def open_simulation_run(
    simulation: Simulation,
    events: EventLog,
    *,
    speed: float,
    loop: bool,
    seed: int | None,
    client_factory: ClientFactory = PakClient,
) -> AsyncIterator[SimulationExecution]:
    """Create clients and PAK runs, then close clients after run cleanup finishes."""
    run_seed = seed if seed is not None else random.SystemRandom().getrandbits(128)

    async with AsyncExitStack() as stack:
        runs: list[PakRun] = []

        for pak in simulation.paks:
            client = client_factory(
                server=simulation.server,
                client_id=pak.client_id,
                access_key=pak.access_key,
                verify=simulation.verify_tls,
            )
            stack.push_async_callback(client.aclose)
            runs.append(
                PakRun(
                    pak,
                    simulation.sessions,
                    client,
                    speed=speed,
                    loop=loop,
                    seed=run_seed,
                    events=events,
                )
            )

        yield SimulationExecution(tuple(runs))
