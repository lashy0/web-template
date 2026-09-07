from collections.abc import Generator

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.api.errors import ERROR_STATUS_CODES, install_error_handlers
from app.auth.exceptions import (
    OAuthClientAlreadyExistsError,
    OAuthClientNotFoundError,
    OAuthProviderUnavailableError,
)
from app.core.exceptions import AppError, ConflictError


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


def domain_errors():
    import importlib
    import inspect
    from pathlib import Path

    paths = [Path("app/auth/exceptions.py"), *Path("app/modules").glob("*/exceptions.py")]
    for path in paths:
        module = importlib.import_module(".".join(path.with_suffix("").parts))
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(cls, AppError)
                and cls.__module__ == module.__name__
                and "code" in cls.__dict__
            ):
                yield cls


@pytest.mark.unit
@pytest.mark.parametrize("error", list(domain_errors()), ids=lambda cls: cls.__name__)
def test_every_concrete_domain_error_has_one_category_and_preserves_payload(error_app, error):
    categories = [base for base in ERROR_STATUS_CODES if issubclass(error, base)]
    assert len(categories) == 1, f"Explicitly classify {error.__name__}"
    error_app.state.error = error("Public explanation", details={"private": "secret"})
    with TestClient(error_app) as client:
        response = client.get("/")
    assert response.status_code == ERROR_STATUS_CODES[categories[0]]
    assert response.json() == {
        "code": error.code,
        "message": "Public explanation",
        "request_id": "",
    }


@pytest.mark.unit
def test_unknown_application_error_is_logged_and_sanitized(error_app, mocker):
    log = mocker.patch("app.api.errors.logger")
    error_app.state.error = AppError("SQL password=secret", details={"token": "secret"})
    with TestClient(error_app) as client:
        response = client.get("/")
    assert response.status_code == 500
    assert response.json() == {
        "code": "application_error",
        "message": "Internal server error",
        "request_id": "",
    }
    log.bind.return_value.opt.return_value.error.assert_called_once()


@pytest.mark.unit
def test_new_subclass_inherits_category_and_request_id(error_app):
    class FutureConflict(ConflictError):
        code = "future_conflict"

    @error_app.middleware("http")
    async def request_id(request, call_next):
        request.state.request_id = "request-42"
        return await call_next(request)

    error_app.state.error = FutureConflict()
    with TestClient(error_app) as client:
        response = client.get("/")
    assert response.status_code == 409
    assert response.json()["request_id"] == "request-42"
