from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from pak_simulator.config import schema

pytestmark = pytest.mark.unit


def test_generated_schema_matches_editor_file() -> None:
    path = Path(__file__).parents[3] / "scenario.schema.json"
    document = schema()

    assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(document)
    assert json.loads(path.read_text(encoding="utf-8")) == document


def test_editor_schema_accepts_demo_template() -> None:
    path = Path(__file__).parents[3] / "scenarios" / "demo.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    Draft202012Validator(schema(), format_checker=Draft202012Validator.FORMAT_CHECKER).validate(data)


@pytest.mark.parametrize(
    "limits, valid",
    [([1, None], True), ([1], False), ([1, 2, 3], False), (["wrong", 2], False)],
)
def test_editor_schema_validates_limit_tuple(
    scenario_data: dict[str, Any],
    limits: list[Any],
    valid: bool,
) -> None:
    scenario_data["profiles"]["p"]["checks"][0]["limits"] = limits

    assert Draft202012Validator(schema()).is_valid(scenario_data) is valid
