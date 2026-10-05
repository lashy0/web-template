from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx2
import msgspec
import pytest
import typer

from pak_simulator.cli import create_app
from pak_simulator.contracts import ClientFactory


@pytest.fixture
def application(client_factory: ClientFactory) -> typer.Typer:
    health = httpx2.MockTransport(
        lambda _: httpx2.Response(
            200,
            json={
                "database_status": "online",
                "kratos_status": "online",
                "hydra_status": "online",
            },
        )
    )

    return create_app(client_factory=client_factory, health_transport=health)


@pytest.fixture
def scenario_path(tmp_path: Path, scenario_data: dict[str, Any]) -> Path:
    path = tmp_path / "scenario.yaml"
    scenario_data["sessions"] = {"start": 0, "swap": 0, "retest": {"chance": 0}}
    profile = scenario_data["profiles"]["p"]
    profile["checks"][0].update(value="1..2", limits=[1, 2])
    profile["defects"] = {"fault": {"chance": 1, "steps": {"test": -1}}}
    path.write_bytes(msgspec.yaml.encode(scenario_data))

    return path
