"""The OpenAPI contract the frontend client is generated from."""

from __future__ import annotations

import pytest

from app.server.asgi import create_app

pytestmark = pytest.mark.unit

_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def test_operation_ids_are_unique() -> None:
    paths = create_app().openapi_schema.to_schema()["paths"]

    operation_ids = [
        operation["operationId"]
        for path_item in paths.values()
        for method, operation in path_item.items()
        if method in _METHODS
    ]

    assert len(operation_ids) == len(set(operation_ids))
