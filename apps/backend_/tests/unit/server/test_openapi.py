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
        "ListKgPrefixes",
        "ListKgVersions",
        "ListPakDevices",
        "ListProductionOrders",
        "ListUsers",
    }
