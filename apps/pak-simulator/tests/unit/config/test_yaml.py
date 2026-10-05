from pathlib import Path
from typing import Any

import pytest

from pak_simulator.config import ScenarioError, load
from tests.unit.config.support import write_scenario

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "text, key, line, column",
    [
        ("server: http://first\nserver: http://second\n", "server", 2, 1),
        ("profiles:\n  p: {}\n  p: {}\n", "p", 3, 3),
        ("paks:\n  - access_key: private-first\n    access_key: private-second\n", "access_key", 3, 5),
        ("profiles:\n  p: {pass_rate: 1, pass_rate: 0}\n", "pass_rate", 2, 21),
        ("profiles:\n  p:\n    <<: {}\n    <<: {}\n", "<<", 4, 5),
    ],
)
def test_duplicate_yaml_keys_rejected(tmp_path: Path, text: str, key: str, line: int, column: int) -> None:
    path = tmp_path / "duplicate.yaml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ScenarioError) as exc_info:
        load(path, environ={})

    message = str(exc_info.value)
    assert str(path) in message
    assert f"Duplicate YAML key {key!r}" in message
    assert f"line {line}, column {column}" in message
    assert "private-first" not in message and "private-second" not in message


def test_yaml_merges_allow_local_overrides(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    path = write_scenario(tmp_path, scenario_data)
    text = path.read_text(encoding="utf-8")
    text = text.replace("  p:\n", "  p: &base\n", 1)
    text += "  selected:\n    <<: &derived\n      <<: *base\n      firmware_version: intermediate\n    firmware_version: selected\n"
    text = text.replace("profile: p\n", "profile: selected\n", 1)
    path.write_text(text, encoding="utf-8")

    simulation = load(path, environ={})

    assert simulation.paks[0].profile.firmware_version == "selected"


def test_invalid_yaml_reported_as_scenario_error(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("paks: [\n", encoding="utf-8")

    with pytest.raises(ScenarioError, match="expected") as exc_info:
        load(path, environ={})

    assert str(path) in str(exc_info.value)
