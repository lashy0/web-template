from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from litestar.status_codes import HTTP_503_SERVICE_UNAVAILABLE
from litestar.testing import AsyncTestClient
from sqlalchemy.exc import OperationalError

from app.server.asgi import create_app

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.unit,
]


@pytest.fixture(autouse=True)
def _dependencies_online() -> Iterator[None]:
    """Every test takes one dependency offline; the others answer."""
    with (
        patch("sqlalchemy.ext.asyncio.AsyncSession.execute", new=AsyncMock()),
        patch("app.lib.hydra.HydraClient.is_ready", new=AsyncMock(return_value=True)),
        patch("app.lib.kratos.KratosClient.is_ready", new=AsyncMock(return_value=True)),
    ):
        yield


async def test_health_endpoint_db_offline() -> None:
    with patch(
        "sqlalchemy.ext.asyncio.AsyncSession.execute",
        side_effect=OperationalError("connection failed", None, Exception("orig")),
    ):
        async with AsyncTestClient(app=create_app()) as client:
            response = await client.get("/health")

    assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["database_status"] == "offline"


async def test_health_endpoint_hydra_offline() -> None:
    with patch("app.lib.hydra.HydraClient.is_ready", new=AsyncMock(return_value=False)):
        async with AsyncTestClient(app=create_app()) as client:
            response = await client.get("/health")

    assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["hydra_status"] == "offline"


async def test_health_endpoint_kratos_offline() -> None:
    with patch("app.lib.kratos.KratosClient.is_ready", new=AsyncMock(return_value=False)):
        async with AsyncTestClient(app=create_app()) as client:
            response = await client.get("/health")

    assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["kratos_status"] == "offline"
