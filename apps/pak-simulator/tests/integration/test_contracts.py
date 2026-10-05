"""Check the simulator's wire contracts against the exported backend OpenAPI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import msgspec
import pytest

from pak_simulator.contracts import (
    SessionComplete,
    SessionOpen,
    SessionResponse,
    StepComplete,
    StepResponse,
    StepStart,
)

pytestmark = pytest.mark.integration

_REQUEST_OPERATIONS = (
    (
        SessionOpen,
        "VerificationSessionOpen",
        "/api/machine/verification/sessions",
        "post",
        "201",
        "VerificationSession",
    ),
    (
        StepStart,
        "VerificationStepStart",
        "/api/machine/verification/sessions/{session_id}/steps",
        "post",
        "201",
        "VerificationStep",
    ),
    (
        StepComplete,
        "VerificationStepComplete",
        "/api/machine/verification/sessions/{session_id}/steps/{step_no}",
        "put",
        "200",
        "VerificationStep",
    ),
    (
        SessionComplete,
        "VerificationSessionComplete",
        "/api/machine/verification/sessions/{session_id}/complete",
        "post",
        "200",
        "VerificationSession",
    ),
)
_SCHEMA_CONSTRAINTS = frozenset(
    {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "pattern"}
)


@pytest.fixture
def backend_openapi() -> dict[str, Any]:
    root = Path(__file__).parents[4]
    document = json.loads((root / "packages/api-client/openapi.json").read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _resolve_schema(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    reference = schema.get("$ref")
    if reference is None:
        return schema

    prefix = "#/components/schemas/"
    assert reference.startswith(prefix)
    resolved = components[reference.removeprefix(prefix)]
    assert isinstance(resolved, dict)
    return resolved


def _wire_types(schema: dict[str, Any], components: dict[str, Any]) -> set[str]:
    schema = _resolve_schema(schema, components)
    alternatives = schema.get("anyOf", schema.get("oneOf"))
    if alternatives is not None:
        return set().union(*(_wire_types(alternative, components) for alternative in alternatives))

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return set(schema_type)
    if isinstance(schema_type, str):
        return {schema_type}
    if "enum" in schema and all(isinstance(value, str) for value in schema["enum"]):
        return {"string"}

    raise AssertionError(f"OpenAPI schema has no wire type: {schema}")


@pytest.mark.parametrize(
    "wire_type, backend_name, path, method, success_status, response_name",
    _REQUEST_OPERATIONS,
)
def test_request_contract_matches_backend_operation(
    wire_type: type[msgspec.Struct],
    backend_name: str,
    path: str,
    method: str,
    success_status: str,
    response_name: str,
    backend_openapi: dict[str, Any],
) -> None:
    components = backend_openapi["components"]["schemas"]
    operation = backend_openapi["paths"][path][method]
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    assert _resolve_schema(request_schema, components) is components[backend_name]

    local = msgspec.json.schema(wire_type)["$defs"][wire_type.__name__]
    backend = components[backend_name]
    assert set(local["properties"]) == set(backend["properties"])
    assert set(local["required"]) == set(backend["required"])

    for field, local_property in local["properties"].items():
        backend_property = backend["properties"][field]
        assert _wire_types(local_property, components) == _wire_types(backend_property, components)

        local_enum_schema = _resolve_schema(local_property, components)
        backend_enum_schema = _resolve_schema(backend_property, components)
        if "enum" in local_enum_schema:
            assert set(local_enum_schema["enum"]) == set(backend_enum_schema["enum"])

        for constraint in _SCHEMA_CONSTRAINTS.intersection(backend_property):
            assert local_property.get(constraint) == backend_property[constraint]

    response_schema = operation["responses"][success_status]["content"]["application/json"]["schema"]
    assert _resolve_schema(response_schema, components) is components[response_name]


@pytest.mark.parametrize(
    "wire_type, backend_name",
    [
        (SessionResponse, "VerificationSession"),
        (StepResponse, "VerificationStep"),
    ],
)
def test_response_contract_covers_consumed_backend_fields(
    wire_type: type[msgspec.Struct], backend_name: str, backend_openapi: dict[str, Any]
) -> None:
    components = backend_openapi["components"]["schemas"]
    local = msgspec.json.schema(wire_type)["$defs"][wire_type.__name__]
    backend = components[backend_name]

    # Response structs intentionally model only what the simulator reads.
    for field, local_property in local["properties"].items():
        assert field in backend["properties"]
        backend_property = backend["properties"][field]
        assert _wire_types(local_property, components) == _wire_types(backend_property, components)
