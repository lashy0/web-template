import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_liveness(
    app: FastAPI,
    client: TestClient,
    api_prefix: str
) -> None:
    response = client.get(f"{api_prefix}/health/live")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ok",
        "version": app.version
    }


@pytest.mark.integration
def test_readiness(
    app: FastAPI,
    client: TestClient,
    api_prefix: str
) -> None:
    response = client.get(f"{api_prefix}/health/ready")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ready",
        "checks": {
            "postgres": "up"
        },
    }
