from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from pak_simulator.config import ScenarioError, load
from tests.unit.config.support import write_scenario

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("source", ["caller", "dotenv"])
def test_environment_key_preserves_yaml_characters(
    tmp_path: Path,
    scenario_data: dict[str, Any],
    source: str,
) -> None:
    secret = '  quoted"key: #literal\nsecond line  '
    scenario_data["paks"][0]["access_key"] = "${SECRET}"
    path = write_scenario(tmp_path, scenario_data)

    environ = {"SECRET": secret} if source == "caller" else {}

    if source == "dotenv":
        (tmp_path / ".env").write_text(f"export SECRET='{secret}'\n", encoding="utf-8")

    simulation = load(path, environ=environ)

    assert simulation.paks[0].access_key == secret


def test_environment_does_not_leak_between_loads(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["paks"][0]["access_key"] = "${PAK_TEST_KEY}"
    path = write_scenario(tmp_path, scenario_data)
    env_file = tmp_path / ".env"
    env_file.write_text("PAK_TEST_KEY=first\n", encoding="utf-8")
    load(path, environ={})
    env_file.write_text("PAK_TEST_KEY=second\n", encoding="utf-8")

    simulation = load(path, environ={})

    assert simulation.paks[0].access_key == "second"


def test_load_leaves_process_environment_unchanged(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    path = write_scenario(tmp_path, scenario_data)
    (tmp_path / ".env").write_text("PAK_TEST_KEY=local\n", encoding="utf-8")
    before = dict(os.environ)

    load(path, environ={})

    assert dict(os.environ) == before


@pytest.mark.parametrize("environ, expected", [({"SECRET": "caller"}, "caller"), ({}, "local"), (None, "process")])
def test_environment_source_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario_data: dict[str, Any],
    environ: dict[str, str] | None,
    expected: str,
) -> None:
    scenario_data["paks"][0]["access_key"] = "${SECRET}"
    path = write_scenario(tmp_path, scenario_data)
    (tmp_path / ".env").write_text("SECRET=local\n", encoding="utf-8")
    monkeypatch.setenv("SECRET", "process")

    simulation = load(path, environ=environ)

    assert simulation.paks[0].access_key == expected


def test_dotenv_nested_missing_reference_reports_names_without_values(
    tmp_path: Path,
    scenario_data: dict[str, Any],
) -> None:
    scenario_data["paks"][0]["access_key"] = "${SECRET}"
    path = write_scenario(tmp_path, scenario_data)
    (tmp_path / ".env").write_text("SECRET=private-prefix-${MISSING}\n", encoding="utf-8")

    with pytest.raises(ScenarioError) as exc_info:
        load(path, environ={})

    message = str(exc_info.value)
    assert "MISSING" in message
    assert "SECRET" in message
    assert "SECRET -> MISSING" in message
    assert "private-prefix" not in message


def test_dotenv_nested_reference_uses_caller_override(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["paks"][0]["access_key"] = "${SECRET}"
    path = write_scenario(tmp_path, scenario_data)
    (tmp_path / ".env").write_text("BASE=file\nSECRET=prefix-${BASE}\n", encoding="utf-8")

    simulation = load(path, environ={"BASE": "caller"})

    assert simulation.paks[0].access_key == "prefix-caller"


def test_dotenv_empty_reference_is_not_missing(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["paks"][0]["access_key"] = "${SECRET}"
    path = write_scenario(tmp_path, scenario_data)
    (tmp_path / ".env").write_text("EMPTY=\nSECRET=prefix-${EMPTY}\n", encoding="utf-8")

    simulation = load(path, environ={})

    assert simulation.paks[0].access_key == "prefix-"


def test_scenario_environment_overrides_working_directory_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario_data: dict[str, Any]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("BASE=working\n", encoding="utf-8")
    scenario_dir = tmp_path / "scenario"
    scenario_dir.mkdir()
    scenario_data["paks"][0]["access_key"] = "${SECRET}"
    path = write_scenario(scenario_dir, scenario_data)
    (scenario_dir / ".env").write_text("BASE=scenario\nSECRET=prefix-${BASE}\n", encoding="utf-8")

    simulation = load(path, environ={})

    assert simulation.paks[0].access_key == "prefix-scenario"


def test_unused_dotenv_entry_with_missing_reference_is_ignored(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    path = write_scenario(tmp_path, scenario_data)
    (tmp_path / ".env").write_text("UNUSED=${MISSING}\n", encoding="utf-8")

    assert load(path, environ={}).paks[0].code == "P"


def test_environment_count_expands_as_integer(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["paks"][0]["dev_eui"] = {"from": "0000000000000001", "count": "${COUNT}"}
    path = write_scenario(tmp_path, scenario_data)

    simulation = load(path, environ={"COUNT": "2"})

    assert simulation.paks[0].dev_euis == ("0000000000000001", "0000000000000002")


def test_missing_environment_variable_rejected(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["paks"][0]["client_id"] = "${PAK_TEST_MISSING}"
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})


def test_circular_dotenv_reference_rejected(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["paks"][0]["access_key"] = "${FIRST}"
    path = write_scenario(tmp_path, scenario_data)
    (tmp_path / ".env").write_text("FIRST=${SECOND}\nSECOND=${FIRST}\n", encoding="utf-8")

    with pytest.raises(ScenarioError):
        load(path, environ={})


def test_invalid_dotenv_encoding_reports_file(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    path = write_scenario(tmp_path, scenario_data)
    env_file = tmp_path / ".env"
    env_file.write_bytes(b"SECRET=private-key-\xff\n")

    with pytest.raises(ScenarioError) as exc_info:
        load(path, environ={})

    message = str(exc_info.value)
    assert str(env_file) in message and "UTF-8" in message
    assert "private-key" not in message
