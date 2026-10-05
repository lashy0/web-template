from __future__ import annotations

from unittest.mock import AsyncMock

import httpx2
import pytest

from pak_simulator.contracts import ClientFactory
from pak_simulator.model import Pak, Sessions, Simulation
from pak_simulator.preflight import check_remote

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


@pytest.mark.parametrize("healthy", [True, False])
async def test_health_and_credentials_report_independently(
    pak: Pak,
    sessions: Sessions,
    client_factory: ClientFactory,
    client: AsyncMock,
    healthy: bool
) -> None:
    simulation = Simulation("http://backend", True, sessions, (pak,), (pak.profile,))

    health = {
        "database_status": "online" if healthy else "offline",
        "kratos_status": "online",
        "hydra_status": "online",
    }
    transport = httpx2.MockTransport(lambda _: httpx2.Response(200 if healthy else 503, json=health))

    probes = [
        probe async for probe in check_remote(simulation, client_factory=client_factory, health_transport=transport)
    ]

    assert [probe.status for probe in probes] == (["OK", "OK"] if healthy else ["ERROR", "OK"])
    assert client.authenticate.await_count == 1 and client.open_session.await_count == 0


@pytest.mark.parametrize("status", [404, 200])
async def test_unexpected_health_response_is_error(pak: Pak, sessions: Sessions, status: int) -> None:
    simulation = Simulation("http://backend", True, sessions, (pak,), (pak.profile,))
    transport = httpx2.MockTransport(lambda _: httpx2.Response(status, text="not health JSON"))
    iterator = check_remote(simulation, health_transport=transport)

    probe = await anext(iterator)
    await iterator.aclose()

    assert probe.status == "ERROR"
