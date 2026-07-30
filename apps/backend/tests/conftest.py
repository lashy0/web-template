import asyncio
import sys
from collections.abc import Generator
from typing import Any

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
    backend_options: dict[str, Any] = {}

    if sys.platform == "win32":
        backend_options["loop_factory"] = asyncio.SelectorEventLoop

    with TestClient(
        app,
        backend_options=backend_options,
    ) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def api_prefix(test_settings: Settings) -> str:
    return test_settings.API_PREFIX
