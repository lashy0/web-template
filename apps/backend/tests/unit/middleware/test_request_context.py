from uuid import UUID

import pytest
from starlette.datastructures import Headers

from app.middleware.request_context import resolve_request_id


@pytest.mark.unit
@pytest.mark.parametrize(
    "request_id",
    [
        pytest.param("550e8400-e29b-41d4-a716-446655440000", id="uuid"),
        pytest.param("01J2QX5M7NCG9F4K8T3V6B1D0E", id="ulid"),
        pytest.param("gateway.request_id:01", id="safe-separators"),
        pytest.param("a" * 64, id="maximum-length"),
    ],
)
def test_resolve_request_id_accepts_safe_value(request_id: str) -> None:
    headers = Headers({"x-request-id": request_id})

    assert resolve_request_id(headers) == request_id


@pytest.mark.unit
@pytest.mark.parametrize(
    "request_id",
    [
        pytest.param("", id="empty"),
        pytest.param("a" * 65, id="too-long"),
        pytest.param(" request-id", id="leading-space"),
        pytest.param("request id", id="embedded-space"),
        pytest.param("request\tid", id="tab"),
        pytest.param("request/id", id="unsupported-separator"),
        pytest.param("réquest", id="non-ascii"),
    ],
)
def test_resolve_request_id_replaces_unsafe_value(request_id: str) -> None:
    headers = Headers({"x-request-id": request_id})

    result = resolve_request_id(headers)

    assert result != request_id
    assert UUID(result).version == 4


@pytest.mark.unit
def test_resolve_request_id_generates_value_when_header_is_missing() -> None:
    result = resolve_request_id(Headers())

    assert UUID(result).version == 4


@pytest.mark.unit
def test_resolve_request_id_replaces_duplicate_values() -> None:
    headers = Headers(
        raw=[
            (b"x-request-id", b"first-id"),
            (b"x-request-id", b"second-id"),
        ]
    )

    result = resolve_request_id(headers)

    assert result not in {"first-id", "second-id"}
    assert UUID(result).version == 4
