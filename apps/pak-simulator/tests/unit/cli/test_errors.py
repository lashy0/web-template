from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, call

import pytest
import typer
from typer.testing import CliRunner

from pak_simulator.cli import create_app
from pak_simulator.client import PakClient
from pak_simulator.errors import ApiError

pytestmark = pytest.mark.unit


def test_run_command_api_failure_exits_nonzero(
    application: typer.Typer,
    client: AsyncMock,
    scenario_path: Path,
) -> None:
    client.open_session.side_effect = ApiError(500, None, "Intentional failure")

    result = CliRunner().invoke(application, ["run", str(scenario_path), "--once", "--log"])

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "Simulation ended with errors" in result.output
    assert "Execution errors: 1" in result.output
    assert client.open_session.await_count == 1 and client.start_step.await_count == 0


@pytest.mark.parametrize("display", ["--log", "--live"])
def test_run_command_internal_failure_reports_error_and_exits_nonzero(
    application: typer.Typer,
    client: AsyncMock,
    scenario_path: Path,
    display: str,
) -> None:
    client.complete_step.side_effect = RuntimeError("Intentional internal failure")

    result = CliRunner().invoke(application, ["run", str(scenario_path), "--once", display])

    assert result.exit_code == 1 and "Simulation ended with errors" in result.output
    assert isinstance(result.exception, SystemExit)
    assert client.complete_session.await_args_list == [call("session-1", "aborted")]


def test_unknown_pak_rejected(application: typer.Typer, scenario_path: Path, client: AsyncMock) -> None:
    result = CliRunner().invoke(application, ["run", str(scenario_path), "--once", "--pak", "missing"])

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "No such PAK in the scenario: missing" in result.output
    assert not client.mock_calls


def test_invalid_delay_rejected(application: typer.Typer, scenario_path: Path, client: AsyncMock) -> None:
    result = CliRunner().invoke(application, ["run", str(scenario_path), "--once", "--start-delay", "3s..1s"])

    assert result.exit_code == 2
    assert isinstance(result.exception, SystemExit)
    assert "--start-delay" in result.output and "the range starts above its end" in result.output
    assert not client.mock_calls


def test_missing_scenario_exits_nonzero(application: typer.Typer, tmp_path: Path, client: AsyncMock) -> None:
    path = tmp_path / "missing.yaml"
    result = CliRunner().invoke(application, ["check", str(path), "--offline"])

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    message = " ".join(result.output.split())
    assert "Cannot read" in message and "missing.yaml" in message
    assert "the file or parent directory does not exist" in message
    assert not client.mock_calls


def test_interrupt_exits_with_130(scenario_path: Path) -> None:
    def interrupted_factory(*, server: str, client_id: str, access_key: str, verify: bool) -> PakClient:
        raise KeyboardInterrupt

    application = create_app(client_factory=interrupted_factory)

    result = CliRunner().invoke(application, ["run", str(scenario_path), "--once", "--log"])

    assert result.exit_code == 130
    assert isinstance(result.exception, SystemExit)
    assert "Stopped." in result.output


def test_nonfinite_speed_rejected(application: typer.Typer, scenario_path: Path, client: AsyncMock) -> None:
    result = CliRunner().invoke(application, ["run", str(scenario_path), "--once", "--speed", "nan"])

    assert result.exit_code == 2
    assert isinstance(result.exception, SystemExit)
    assert "--speed" in result.output and "Speed must be a finite number" in result.output
    assert not client.mock_calls


def test_cyclic_yaml_reports_configuration_error(
    application: typer.Typer,
    scenario_path: Path,
    client: AsyncMock,
) -> None:
    text = scenario_path.read_text(encoding="utf-8") + "\nunexpected: &cycle [*cycle]\n"
    scenario_path.write_text(text, encoding="utf-8")

    result = CliRunner().invoke(application, ["run", str(scenario_path), "--once", "--log"])

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "Circular YAML reference" in result.output and "unexpected" in result.output
    assert "RecursionError" not in result.output and "Traceback" not in result.output
    assert not client.mock_calls
