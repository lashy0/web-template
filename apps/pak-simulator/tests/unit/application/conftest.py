from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from pak_simulator.contracts import ClientFactory, VerificationClient
from pak_simulator.model import Pak, Sessions, Simulation
from tests.unit.application.support import make_simulation
from tests.unit.support import make_client


@pytest.fixture
def paired_simulation(pak: Pak, sessions: Sessions) -> Simulation:
    other = replace(pak, code="OTHER", client_id="other", dev_euis=("0000000000000003", "0000000000000004"))

    return replace(make_simulation(pak, sessions), paks=(pak, other))


@pytest.fixture
def paired_clients() -> dict[str, AsyncMock]:
    return {"client": make_client(), "other": make_client()}


@pytest.fixture
def paired_factory(paired_clients: dict[str, AsyncMock]) -> ClientFactory:
    def factory(*, server: str, client_id: str, access_key: str, verify: bool) -> VerificationClient:
        return paired_clients[client_id]

    return factory
