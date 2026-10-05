from __future__ import annotations

import asyncio
from functools import partial
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, call

import msgspec
import pytest
import typer
from typer.testing import CliRunner

from pak_simulator.simulation.runner import PakRun

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("display,pass_rate", [("--log", 0), ("--live", 1)])
def test_run_command_applies_pass_rate_and_finishes(
    application: typer.Typer,
    client: AsyncMock,
    scenario_path: Path,
    display: str,
    pass_rate: int,
) -> None:
    result = CliRunner().invoke(
        application,
        [
            "run",
            str(scenario_path),
            "--once",
            display,
            "--seed",
            "4",
            "--pak",
            "P",
            "--pass-rate",
            str(pass_rate),
            "--start-delay",
            "0s",
            "--session-delay",
            "0s",
        ],
    )

    assert result.exit_code == 0
    assert client.open_session.await_count == 1 and client.complete_step.await_count == 1
    expected_status = "passed" if pass_rate else "failed"
    assert client.complete_session.await_args_list == [call("session-1", expected_status)]
    assert client.complete_step.await_args.kwargs["passed"] is bool(pass_rate)


def test_run_command_selects_requested_pak_and_skips_unconfigured_pak(
    application: typer.Typer,
    client: AsyncMock,
    scenario_path: Path,
    scenario_data: dict[str, Any],
    client_factory: Mock,
) -> None:
    scenario_data["paks"].append(
        {**scenario_data["paks"][0], "code": "OTHER", "client_id": "other", "dev_eui": ["0000000000000002"]}
    )
    scenario_data["paks"][0].update(client_id="${UNCONFIGURED_CLIENT}", access_key="${UNCONFIGURED_KEY}")
    scenario_path.write_bytes(msgspec.yaml.encode(scenario_data))

    result = CliRunner().invoke(application, ["run", str(scenario_path), "--once", "--log", "--pak", "OTHER"])

    assert result.exit_code == 0
    assert [request.kwargs["dev_eui"] for request in client.open_session.await_args_list] == ["0000000000000002"]
    client_factory.assert_called_once_with(server="http://backend", client_id="other", access_key="k", verify=True)


def test_run_command_applies_delays_scaled_by_speed(
    application: typer.Typer,
    client: AsyncMock,
    scenario_path: Path,
    scenario_data: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario_data["paks"][0]["dev_eui"].append("0000000000000002")
    scenario_path.write_bytes(msgspec.yaml.encode(scenario_data))
    delays: list[float] = []

    async def record_sleep(seconds: float) -> None:
        delays.append(seconds)
        await asyncio.sleep(0)

    monkeypatch.setattr("pak_simulator.application.PakRun", partial(PakRun, sleep=record_sleep))
    result = CliRunner().invoke(
        application,
        [
            "run",
            str(scenario_path),
            "--once",
            "--log",
            "--seed",
            "7",
            "--speed",
            "2",
            "--start-delay",
            "2s..4s",
            "--session-delay",
            "500ms",
        ],
    )

    assert result.exit_code == 0 and client.open_session.await_count == 2
    assert 1 <= delays[0] <= 2
    assert 0.25 in delays
