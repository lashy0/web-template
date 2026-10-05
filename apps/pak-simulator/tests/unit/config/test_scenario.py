from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pak_simulator.config import ScenarioError, load
from tests.unit.config.support import write_scenario

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("duration", [float("inf"), float("nan"), -1.0, True, "1s.."])
def test_invalid_duration_rejected(
    tmp_path: Path,
    scenario_data: dict[str, Any],
    duration: float | bool | str,
) -> None:
    scenario_data["profiles"]["p"]["checks"][0]["time"] = duration
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError, match=r"\$\.profiles\.p\.checks\[0\]\.time:"):
        load(path, environ={})


@pytest.mark.parametrize("field", ["name", "label", "group"])
def test_blank_check_field_rejected(tmp_path: Path, scenario_data: dict[str, Any], field: str) -> None:
    scenario_data["profiles"]["p"]["checks"][0][field] = " "
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})


def test_blank_firmware_rejected(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["profiles"]["p"]["firmware_version"] = " "
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})


@pytest.mark.parametrize("field", ["client_id", "access_key", "code"])
def test_blank_pak_field_rejected(tmp_path: Path, scenario_data: dict[str, Any], field: str) -> None:
    scenario_data["paks"][0][field] = " "
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})


def test_unknown_yaml_field_rejected(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["typo"] = True
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})


def test_nonfinite_measurement_limits_rejected(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["profiles"]["p"]["checks"][0]["limits"] = [0, float("inf")]
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})


@pytest.mark.parametrize(
    "server",
    [
        "ftp://backend",
        "http://backend:bad",
        "http://backend:99999",
        "http://backend?query=1",
        "http://bad host",
        "http:backend",
        "https:///backend",
        "http://backend#",
        "http://backend?",
    ],
)
def test_invalid_server_rejected(tmp_path: Path, scenario_data: dict[str, Any], server: str) -> None:
    scenario_data["server"] = server
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})


def test_unknown_profile_rejected(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["paks"][0]["profile"] = "missing"
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})


@pytest.mark.parametrize("field, length", [("name", 129), ("label", 256), ("group", 33)])
def test_check_fields_respect_backend_lengths(
    tmp_path: Path,
    scenario_data: dict[str, Any],
    field: str,
    length: int,
) -> None:
    scenario_data["profiles"]["p"]["checks"][0][field] = "x" * length
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})


def test_unknown_defect_target_rejected(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["profiles"]["p"]["defects"] = {"fault": {"chance": 1, "steps": {"missing": 0}}}
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})


def test_zero_limits_mean_no_limits(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["profiles"]["p"]["checks"][0]["limits"] = [0, 0]
    path = write_scenario(tmp_path, scenario_data)

    check = load(path, environ={}).profiles[0].checks[0]

    assert check.low is None and check.high is None


def test_reversed_limits_rejected(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["profiles"]["p"]["checks"][0]["limits"] = [2, 1]
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})


def test_validation_diagnostic_omits_nested_input_values(
    tmp_path: Path,
    scenario_data: dict[str, Any],
) -> None:
    scenario_data["paks"][0]["access_key"] = {"secret": "private-nested-key"}
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError) as exc_info:
        load(path, environ={})

    message = str(exc_info.value)
    assert "$.paks[0].access_key: Input should be a valid string" in message
    assert "private-nested-key" not in message
