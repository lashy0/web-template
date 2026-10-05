from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pak_simulator.config import ScenarioError, load
from tests.unit.config.support import write_scenario

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("pak_codes", [None, ["P"]])
def test_duplicate_pak_codes_rejected(
    tmp_path: Path,
    scenario_data: dict[str, Any],
    pak_codes: list[str] | None,
) -> None:
    scenario_data["paks"].append({**scenario_data["paks"][0], "client_id": "second", "dev_eui": ["0000000000000002"]})
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError, match="PAK codes in `paks` repeat"):
        load(path, pak_codes=pak_codes, environ={})


def test_duplicate_oauth_clients_rejected_without_credentials(
    tmp_path: Path,
    scenario_data: dict[str, Any],
) -> None:
    first = scenario_data["paks"][0]
    first["client_id"] = "private-client-id"
    first["access_key"] = "private-access-key"
    scenario_data["paks"].append(
        {**first, "code": "SECOND", "access_key": "another-private-key", "dev_eui": ["0000000000000002"]}
    )
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError, match="OAuth client ID") as exc_info:
        load(path, environ={})

    message = str(exc_info.value)
    assert "P" in message and "SECOND" in message
    assert "private-client-id" not in message and "private-access-key" not in message
    assert "another-private-key" not in message


@pytest.mark.parametrize("source", ["missing", "nested", "absent"])
def test_server_override_does_not_require_original_address(
    tmp_path: Path,
    scenario_data: dict[str, Any],
    source: str,
) -> None:
    scenario_data["server"] = "${ORIGINAL_SERVER}"

    if source == "nested":
        (tmp_path / ".env").write_text("ORIGINAL_SERVER=${MISSING_HOST}\n", encoding="utf-8")
    elif source == "absent":
        del scenario_data["server"]

    path = write_scenario(tmp_path, scenario_data)

    simulation = load(path, server="http://override:8000", environ={})

    assert simulation.server == "http://override:8000"


def test_pak_selection_ignores_other_settings_and_profiles(
    tmp_path: Path,
    scenario_data: dict[str, Any],
) -> None:
    scenario_data["paks"][0]["code"] = " ${SELECTED_CODE} "
    scenario_data["paks"][0]["profile"] = "${SELECTED_PROFILE}"
    scenario_data["paks"].append(
        {"code": "${OTHER_CODE}", "client_id": "${OTHER_CLIENT}", "access_key": "${OTHER_KEY}", "profile": "unused"}
    )
    scenario_data["profiles"]["unused"] = {"firmware_version": "${OTHER_FIRMWARE}", "checks": "invalid"}
    (tmp_path / ".env").write_text("OTHER_CLIENT=${MISSING}\nOTHER_KEY=${OTHER_KEY}\n", encoding="utf-8")
    path = write_scenario(tmp_path, scenario_data)

    simulation = load(
        path, pak_codes=["P", "P"], environ={"SELECTED_CODE": "P", "OTHER_CODE": "OTHER", "SELECTED_PROFILE": "p"}
    )

    assert [pak.code for pak in simulation.paks] == ["P"]
    assert [profile.key for profile in simulation.profiles] == ["p"]

    with pytest.raises(ScenarioError):
        load(path, pak_codes=["OTHER"], environ={"SELECTED_CODE": "P", "OTHER_CODE": "OTHER"})


@pytest.mark.parametrize(
    "paks, field, reason",
    [
        (None, "$.paks", "Input should be a valid list"),
        ([None], "$.paks[1]", "Input should be a valid dictionary"),
        ([{"code": 1}], "$.paks[1].code", "Input should be a valid string"),
        ([{"profile": "p"}], "$.paks[1].code", "Field required"),
    ],
)
def test_pak_selection_preserves_input_validation(
    tmp_path: Path,
    scenario_data: dict[str, Any],
    paks: list[Any] | None,
    field: str,
    reason: str,
) -> None:
    # Keep P selectable so lookup errors cannot mask malformed entries.
    first = scenario_data["paks"][0]
    other_fields = {key: value for key, value in first.items() if key != "code"}
    scenario_data["paks"] = (
        None if paks is None else [first, *({**other_fields, **pak} if isinstance(pak, dict) else pak for pak in paks)]
    )
    path = write_scenario(tmp_path, scenario_data)

    with pytest.raises(ScenarioError) as exc_info:
        load(path, pak_codes=["P"], environ={})

    message = str(exc_info.value)
    assert reason in message and field in message


def test_multiple_pak_selection_preserves_order_and_shared_profile(
    tmp_path: Path,
    scenario_data: dict[str, Any],
) -> None:
    first = scenario_data["paks"][0]
    scenario_data["paks"].extend(
        [
            {"code": "UNUSED", "access_key": "${MISSING}"},
            {**first, "code": "SECOND", "client_id": "second", "dev_eui": ["0000000000000002"]},
        ]
    )
    path = write_scenario(tmp_path, scenario_data)

    simulation = load(path, pak_codes=["SECOND", "P"], environ={})

    assert [pak.code for pak in simulation.paks] == ["P", "SECOND"]
    assert len(simulation.profiles) == 1 and simulation.paks[0].profile is simulation.paks[1].profile
    assert simulation.paks[0].access_key == simulation.paks[1].access_key == first["access_key"]

    with pytest.raises(ScenarioError, match="No such PAK in the scenario: unknown"):
        load(path, pak_codes=["P", "unknown"], environ={})


@pytest.mark.parametrize("unused_key", ["${MISSING_PROFILE}", "${CIRCULAR_PROFILE}"])
def test_selection_ignores_unresolved_unused_profile_keys(
    tmp_path: Path,
    scenario_data: dict[str, Any],
    unused_key: str,
) -> None:
    scenario_data["profiles"]["${SELECTED_PROFILE}"] = scenario_data["profiles"].pop("p")
    scenario_data["profiles"][unused_key] = {"checks": "invalid"}
    (tmp_path / ".env").write_text("CIRCULAR_PROFILE=${CIRCULAR_PROFILE}\n", encoding="utf-8")
    path = write_scenario(tmp_path, scenario_data)

    simulation = load(path, pak_codes=["P"], environ={"SELECTED_PROFILE": "p"})

    assert [profile.key for profile in simulation.profiles] == ["p"]
    assert simulation.paks[0].profile is simulation.profiles[0]

    with pytest.raises(ScenarioError, match=r"Environment|Circular"):
        load(path, environ={"SELECTED_PROFILE": "p"})
