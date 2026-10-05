from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from pak_simulator.config import ScenarioError, load
from tests.unit.config.support import write_scenario

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("pak_codes,first_key", [(None, "p"), (None, "${PROFILE_A}"), (["P"], "${PROFILE_A}")])
def test_expanded_profile_key_collisions_rejected(
    tmp_path: Path, scenario_data: dict[str, Any], pak_codes: list[str] | None, first_key: str
) -> None:
    first = scenario_data["profiles"].pop("p")
    second = deepcopy(first)
    second["firmware_version"] = "unexpected-profile"
    scenario_data["profiles"] = {first_key: first, "${PROFILE_B}": second}
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError) as exc_info:
        load(path, pak_codes=pak_codes, environ={"PROFILE_A": "p", "PROFILE_B": "p"})

    message = str(exc_info.value)
    assert "Duplicate mapping key after environment expansion" in message
    assert "$['profiles']" in message
    assert repr(first_key) in message and "${PROFILE_B}" in message
    assert "resolve to 'p'" in message


@pytest.mark.parametrize(
    "reference",
    ["&cycle [*cycle]", "&cycle {back: *cycle}", "&first [&second {back: *first}]"],
)
def test_cyclic_yaml_references_rejected(tmp_path: Path, scenario_data: dict[str, Any], reference: str) -> None:
    path = write_scenario(tmp_path, scenario_data)
    path.write_text(path.read_text(encoding="utf-8") + f"\nunexpected: {reference}\n", encoding="utf-8")

    with pytest.raises(ScenarioError) as exc_info:
        load(path, environ={})

    message = str(exc_info.value)
    assert "Circular YAML reference" in message
    assert "$['unexpected']" in message
    assert "refers back to $['unexpected']" in message


def test_shared_yaml_aliases_expand_without_being_treated_as_cycles(
    tmp_path: Path,
    scenario_data: dict[str, Any],
) -> None:
    checks = scenario_data["profiles"]["p"]["checks"]
    checks[0]["label"] = "${LABEL}"
    checks.append(checks[0])
    path = tmp_path / "scenario.yaml"
    text = yaml.safe_dump(scenario_data)
    path.write_text(text, encoding="utf-8")
    assert "&" in text and "*" in text

    simulation = load(path, environ={"LABEL": "Shared check"})

    assert [check.label for check in simulation.paks[0].profile.checks] == ["Shared check", "Shared check"]
