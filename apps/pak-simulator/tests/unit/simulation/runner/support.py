from __future__ import annotations

from pak_simulator.contracts import VerificationClient
from pak_simulator.model import Pak, Sessions
from pak_simulator.simulation.runner import PakRun
from pak_simulator.simulation.session import Sleep
from pak_simulator.simulation.state import EventLog
from tests.unit.support import yield_control


def make_run(
    pak: Pak,
    sessions: Sessions,
    client: VerificationClient,
    *,
    sleep: Sleep = yield_control,
) -> PakRun:
    return PakRun(
        pak,
        sessions,
        client,
        speed=1,
        loop=False,
        seed=4,
        events=EventLog(),
        sleep=sleep,
    )
