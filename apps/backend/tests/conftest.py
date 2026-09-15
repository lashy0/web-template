import asyncio
import sys
from collections.abc import Callable, Generator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.bootstrap.permissions import compose_permission_registry
from app.core.config import Settings
from app.main import create_app
from app.shared.security import install_permission_registry


def _selector_event_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop()


def pytest_asyncio_loop_factories(
    config: pytest.Config,
    item: pytest.Item,
) -> dict[str, Callable[[], asyncio.AbstractEventLoop]]:
    del config, item

    if sys.platform == "win32":
        return {"selector": _selector_event_loop}

    return {"default": asyncio.new_event_loop}


@pytest.fixture(scope="session", autouse=True)
def installed_permissions() -> None:
    """Install the permission registry the way the composition root does.

    Without this, permission checks depend on ``app.main`` having been imported
    (it calls ``create_app()`` at module level), so a role would silently hold
    an empty permission set and rule tests would pass for the wrong reason.
    """
    install_permission_registry(compose_permission_registry())


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
