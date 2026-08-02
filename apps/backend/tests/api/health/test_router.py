import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core.config import Settings
from app.core.version import APP_VERSION


@pytest.mark.api
def test_liveness(app: FastAPI, client: TestClient, api_prefix: str) -> None:
    response = client.get(f"{api_prefix}/health/live")

    assert response.status_code == status.HTTP_200_OK
    assert app.version == APP_VERSION
    assert response.json() == {"status": "ok", "version": APP_VERSION}


@pytest.mark.api
@pytest.mark.parametrize(
    ("postgres_ready", "redis_ready", "expected_code", "expected_status"),
    [
        pytest.param(
            True,
            True,
            status.HTTP_200_OK,
            "ready",
            id="ready",
        ),
        pytest.param(
            False,
            True,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "not_ready",
            id="postgres-down",
        ),
        pytest.param(
            True,
            False,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "not_ready",
            id="redis-down",
        ),
    ],
)
def test_readiness(
    app: FastAPI,
    client: TestClient,
    api_prefix: str,
    mocker: MockerFixture,
    test_settings: Settings,
    postgres_ready: bool,
    redis_ready: bool,
    expected_code: int,
    expected_status: str,
) -> None:
    postgres_ready_mock = mocker.patch(
        "app.modules.health.router.is_postgres_ready",
        return_value=postgres_ready,
    )
    redis_ready_mock = mocker.patch(
        "app.modules.health.router.is_redis_ready",
        return_value=redis_ready,
    )

    response = client.get(f"{api_prefix}/health/ready")

    assert response.status_code == expected_code
    assert response.json() == {
        "status": expected_status,
        "checks": {
            "postgres": "up" if postgres_ready else "down",
            "redis": "up" if redis_ready else "down",
        },
    }

    postgres_ready_mock.assert_awaited_once_with(
        app.state.database.engine,
        timeout=test_settings.READINESS_TIMEOUT,
    )
    redis_ready_mock.assert_awaited_once_with(
        app.state.redis,
        timeout=test_settings.READINESS_TIMEOUT,
    )
