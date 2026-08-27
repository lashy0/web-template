from collections.abc import Generator

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.api.errors import install_error_handlers
from app.auth.exceptions import (
    OAuthClientAlreadyExistsError,
    OAuthClientNotFoundError,
    OAuthProviderUnavailableError,
)


@pytest.fixture
def error_app() -> Generator[FastAPI]:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/", response_model=None)
    def raise_configured_error() -> None:
        raise app.state.error

    yield app


@pytest.mark.unit
@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        pytest.param(
            OAuthClientNotFoundError,
            status.HTTP_404_NOT_FOUND,
            "oauth_client_not_found",
            id="oauth-client-not-found",
        ),
        pytest.param(
            OAuthClientAlreadyExistsError,
            status.HTTP_409_CONFLICT,
            "oauth_client_already_exists",
            id="oauth-client-already-exists",
        ),
        pytest.param(
            OAuthProviderUnavailableError,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "oauth_provider_unavailable",
            id="oauth-provider-unavailable",
        ),
    ],
)
def test_oauth_errors_map_to_api_responses(
    error_app: FastAPI,
    error: type[Exception],
    status_code: int,
    code: str,
) -> None:
    error_app.state.error = error()

    with TestClient(error_app) as client:
        response = client.get("/")

    assert response.status_code == status_code
    assert response.json()["code"] == code
