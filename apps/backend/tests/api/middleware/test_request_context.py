from uuid import UUID

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_response_preserves_safe_request_id(client: TestClient, api_prefix: str) -> None:
    request_id = "client-request.01"

    response = client.get(
        f"{api_prefix}/health/live",
        headers={"x-request-id": request_id},
    )

    assert response.headers["x-request-id"] == request_id


@pytest.mark.api
def test_response_replaces_unsafe_request_id(client: TestClient, api_prefix: str) -> None:
    response = client.get(
        f"{api_prefix}/health/live",
        headers={"x-request-id": "unsafe request id"},
    )

    assert UUID(response.headers["x-request-id"]).version == 4
