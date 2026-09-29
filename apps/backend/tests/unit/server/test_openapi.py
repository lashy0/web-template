"""The OpenAPI contract the frontend client is generated from."""

from __future__ import annotations

from typing import NotRequired, TypedDict, cast

import pytest

from app.server.asgi import create_app

pytestmark = pytest.mark.unit

_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


class _Parameter(TypedDict):
    name: str


class _Operation(TypedDict):
    operationId: str
    parameters: NotRequired[list[_Parameter]]


def test_operation_ids_are_unique() -> None:
    paths = create_app().openapi_schema.to_schema()["paths"]

    operation_ids = [
        operation["operationId"]
        for path_item in paths.values()
        for method, operation in path_item.items()
        if method in _METHODS
    ]

    assert len(operation_ids) == len(set(operation_ids))


def test_archivable_lists_accept_archived_filter() -> None:
    """Update this set when a list of a model with ``archived_at`` is added."""
    paths = cast("dict[str, dict[str, _Operation]]", create_app().openapi_schema.to_schema()["paths"])

    operations_with_filter = {
        path_item["get"]["operationId"]
        for path_item in paths.values()
        if "get" in path_item
        and any(parameter["name"] == "archived" for parameter in path_item["get"].get("parameters", []))
    }

    assert operations_with_filter == {
        "ListBatches",
        "ListDefectGroups",
        "ListDefectTypes",
        "ListKgPrefixes",
        "ListKgVersions",
        "ListPakDevices",
        "ListProductionOrders",
        "ListUsers",
    }


def test_pages_are_components_named_after_the_item() -> None:
    schema = create_app().openapi_schema.to_schema()

    response = schema["paths"]["/api/users"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]

    assert response == {"$ref": "#/components/schemas/UserPage"}
    assert schema["components"]["schemas"]["UserPage"]["required"] == ["items", "limit", "offset", "total"]


def test_request_schemas_carry_field_constraints() -> None:
    """The frontend generates its form rules from these constraints."""
    schemas = create_app().openapi_schema.to_schema()["components"]["schemas"]

    login = schemas["UserCreate"]["properties"]["login"]
    pak_code = schemas["PakDeviceCreate"]["properties"]["code"]

    assert (login["minLength"], login["maxLength"], "pattern" in login) == (3, 64, True)
    assert (pak_code["maxLength"], "pattern" in pak_code) == (128, True)
