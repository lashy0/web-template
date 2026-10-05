from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pak_simulator.config import ScenarioError, load
from tests.unit.config.support import write_scenario

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("selection", [[" 000000000000000a "], {"from": "0000000000000009", "count": 2}])
def test_overlapping_pak_units_rejected(
    tmp_path: Path,
    scenario_data: dict[str, Any],
    selection: list[str] | dict[str, Any],
) -> None:
    first = scenario_data["paks"][0]
    first["dev_eui"] = ["000000000000000A"]
    scenario_data["paks"].append({**first, "code": "SECOND", "client_id": "second", "dev_eui": selection})
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError, match="000000000000000A") as exc_info:
        load(path, environ={})

    assert "SECOND" in str(exc_info.value)


@pytest.mark.parametrize("selection", ["range", "list"])
def test_large_dev_eui_selection_is_allowed(
    tmp_path: Path,
    scenario_data: dict[str, Any],
    selection: str,
) -> None:
    count = 100_001
    scenario_data["paks"][0]["dev_eui"] = (
        {"from": "0000000000000001", "count": count}
        if selection == "range"
        else [f"{number:016X}" for number in range(1, count + 1)]
    )
    path = write_scenario(tmp_path, scenario_data)

    assert len(load(path, environ={}).paks[0].dev_euis) == count


def test_large_total_selection_across_paks_is_allowed(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    first = scenario_data["paks"][0]
    first["dev_eui"] = {"from": "0000000000000001", "count": 50_000}
    scenario_data["paks"].append(
        {
            **first,
            "code": "SECOND",
            "client_id": "second",
            "dev_eui": {"from": "00000000000186A0", "count": 50_001},
        }
    )
    path = write_scenario(tmp_path, scenario_data)

    assert sum(len(pak.dev_euis) for pak in load(path, environ={}).paks) == 100_001


def test_dev_eui_range_overflow_rejected(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["paks"][0]["dev_eui"] = {"from": "FFFFFFFFFFFFFFFF", "count": 2}
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})


def test_invalid_dev_eui_rejected(tmp_path: Path, scenario_data: dict[str, Any]) -> None:
    scenario_data["paks"][0]["dev_eui"] = ["invalid"]
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError):
        load(path, environ={})
