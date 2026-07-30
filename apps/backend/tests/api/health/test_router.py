import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core.version import APP_VERSION


@pytest.mark.api
def test_liveness(app: FastAPI, client: TestClient, api_prefix: str) -> None:
    response = client.get(f"{api_prefix}/health/live")

    assert response.status_code == status.HTTP_200_OK
    assert app.version == APP_VERSION
    assert response.json() == {"status": "ok", "version": APP_VERSION}


@pytest.mark.api
def test_readiness(
    client: TestClient,
    api_prefix: str,
    mocker: MockerFixture,
) -> None:
    postgres_ready_mock = mocker.patch(
        "app.modules.health.router.is_postgres_ready",
        return_value=True,
    )
    redis_ready_mock = mocker.patch(
        "app.modules.health.router.is_redis_ready",
        return_value=True,
    )

    response = client.get(f"{api_prefix}/health/ready")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ready",
        "checks": {
            "postgres": "up",
            "redis": "up",
        },
    }
    postgres_ready_mock.assert_awaited_once()
    redis_ready_mock.assert_awaited_once()
