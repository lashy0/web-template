from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings()


@pytest.fixture(scope="module")
def app(test_settings: Settings) -> FastAPI:
    return create_app(test_settings)


@pytest.fixture(scope="module")
def client(app: FastAPI) -> Generator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def api_prefix(test_settings: Settings) -> str:
    return test_settings.API_PREFIX
