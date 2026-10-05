from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import msgspec
import pytest
import typer
from typer.testing import CliRunner

from pak_simulator.cli import app
from pak_simulator.config import schema

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("arguments", [["--version"], ["-V"], ["--version", "run"]])
def test_version_option_exits_without_scenario_or_network(
    application: typer.Typer,
    client: AsyncMock,
    arguments: list[str],
) -> None:
    result = CliRunner().invoke(application, arguments)

    assert result.exit_code == 0
    assert result.stdout == f"pak-sim {version('pak-simulator')}\n"
    assert not client.mock_calls


@pytest.mark.parametrize("destination", ["stdout", "file"])
def test_schema_command_writes_valid_document(tmp_path: Path, destination: str) -> None:
    output = tmp_path / "schema.json"
    arguments = ["schema"] if destination == "stdout" else ["schema", "--output", str(output)]
    result = CliRunner().invoke(app, arguments)

    assert result.exit_code == 0
    document = result.stdout if destination == "stdout" else output.read_text(encoding="utf-8")
    assert json.loads(document) == schema()


@pytest.mark.parametrize("arguments", [[], ["--help"]])
def test_root_help_shows_version_option(arguments: list[str]) -> None:
    result = CliRunner().invoke(app, arguments)

    assert result.exit_code == (2 if not arguments else 0)
    assert "--version" in result.output and "-V" in result.output


@pytest.mark.parametrize("command,options", [("check", ["--offline"]), ("run", ["--once", "--log"])])
def test_command_server_override_replaces_missing_variable(
    application: typer.Typer,
    scenario_path: Path,
    scenario_data: dict[str, Any],
    command: str,
    options: list[str],
) -> None:
    scenario_data["server"] = "${UNCONFIGURED_SERVER}"
    scenario_path.write_bytes(msgspec.yaml.encode(scenario_data))

    result = CliRunner().invoke(application, [command, str(scenario_path), "--server", "http://backend", *options])

    assert result.exit_code == 0


def test_offline_check_does_not_contact_backend(
    application: typer.Typer,
    client: AsyncMock,
    scenario_path: Path,
) -> None:
    result = CliRunner().invoke(application, ["check", str(scenario_path), "--offline", "--details"])

    assert result.exit_code == 0 and not client.mock_calls


def test_online_check_authenticates_without_sessions(
    application: typer.Typer,
    client: AsyncMock,
    scenario_path: Path,
) -> None:
    result = CliRunner().invoke(application, ["check", str(scenario_path)])

    assert result.exit_code == 0 and client.authenticate.await_count == 1 and client.open_session.await_count == 0
