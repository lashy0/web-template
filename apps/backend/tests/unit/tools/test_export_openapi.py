import json
import sys
from pathlib import Path

import pytest
from fastapi.routing import APIRoute, iter_route_contexts

from app.main import create_app
from tools.export_openapi import AUDIENCE_TAGS, Audience, export_openapi, parse_arguments


@pytest.mark.unit
@pytest.mark.parametrize("audience", ("web", "machine"))
def test_export_openapi_writes_the_audience_schema(
    tmp_path: Path,
    audience: Audience,
) -> None:
    app = create_app()
    output = tmp_path / "generated" / f"{audience}.json"

    export_openapi(app, output, audience)

    schema = json.loads(output.read_text(encoding="utf-8"))
    expected_paths = {
        route_context.path
        for route_context in iter_route_contexts(app.routes)
        if isinstance(route_context.original_route, APIRoute)
        and AUDIENCE_TAGS[audience].intersection(route_context.tags)
    }

    assert set(schema["paths"]) == expected_paths
    assert {
        tag
        for path_item in schema["paths"].values()
        for operation in path_item.values()
        for tag in operation["tags"]
    } <= AUDIENCE_TAGS[audience]
    assert output.read_bytes().endswith(b"\n")


@pytest.mark.unit
def test_parse_arguments_reads_audience(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["export_openapi.py", "--audience", "machine", "--output", str(output)],
    )

    assert parse_arguments() == (output, "machine")
