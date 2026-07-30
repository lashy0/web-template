import pytest
from fastapi import status
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_readiness_with_real_dependencies(
    client: TestClient,
    api_prefix: str,
) -> None:
    response = client.get(f"{api_prefix}/health/ready")

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {
        "status": "ready",
        "checks": {
            "postgres": "up",
            "redis": "up",
        },
    }
