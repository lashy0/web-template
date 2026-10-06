"""Health reports each dependency of a running application."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from litestar.testing import AsyncTestClient
from pydantic import PostgresDsn

from app.server.asgi import create_app

if TYPE_CHECKING:
    from litestar import Litestar

    from app.config import Settings

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]

# Nothing listens on the discard port, so connections are refused at once.
_UNREACHABLE = "127.0.0.1:9"


async def test_health_reports_all_dependencies_online(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get("/api/health")

    body = response.json()
    assert (response.status_code, body["database_status"], body["kratos_status"], body["hydra_status"]) == (
        200,
        "online",
        "online",
        "online",
    )


async def test_version_reports_the_configured_release(settings: Settings) -> None:
    app_settings = settings.app.model_copy(update={"version": "2026.9.1"})

    async with AsyncTestClient(create_app(settings=replace(settings, app=app_settings))) as client:
        response = await client.get("/api/system/version")

    assert (response.status_code, response.json()) == (200, {"version": "2026.9.1"})


async def test_health_reports_offline_database(settings: Settings) -> None:
    db = settings.db.model_copy(
        update={"database_url_override": PostgresDsn(f"postgresql+asyncpg://test:test@{_UNREACHABLE}/test")}
    )

    async with AsyncTestClient(create_app(settings=replace(settings, db=db))) as client:
        response = await client.get("/api/health")

    assert (response.status_code, response.json()["database_status"]) == (503, "offline")


async def test_health_reports_offline_kratos(settings: Settings) -> None:
    kratos = settings.kratos.model_copy(update={"admin_url": f"http://{_UNREACHABLE}"})

    async with AsyncTestClient(create_app(settings=replace(settings, kratos=kratos))) as client:
        response = await client.get("/api/health")

    assert (response.status_code, response.json()["kratos_status"]) == (503, "offline")


async def test_health_reports_offline_hydra(settings: Settings) -> None:
    hydra = settings.hydra.model_copy(update={"admin_url": f"http://{_UNREACHABLE}"})

    async with AsyncTestClient(create_app(settings=replace(settings, hydra=hydra))) as client:
        response = await client.get("/api/health")

    assert (response.status_code, response.json()["hydra_status"]) == (503, "offline")


async def test_event_stream_requires_a_session(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get("/api/events")

    assert response.status_code == 401
