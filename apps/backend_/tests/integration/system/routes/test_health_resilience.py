from unittest.mock import AsyncMock, patch

import pytest
from litestar.status_codes import HTTP_503_SERVICE_UNAVAILABLE
from litestar.testing import AsyncTestClient
from sqlalchemy.exc import OperationalError

from app.lib.kratos import KratosClient
from app.server.asgi import create_app

pytestmark = pytest.mark.anyio


async def test_health_endpoint_db_offline() -> None:
    """Test health endpoint returns 503 and offline status when DB is unreachable.

    It should catch OperationalError and not crash.
    """
    app = create_app()

    with (
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.execute",
            side_effect=OperationalError("connection failed", None, Exception("orig")),
        ),
        patch.object(KratosClient, "is_ready", new=AsyncMock(return_value=True)),
    ):
        async with AsyncTestClient(app=app) as client:
            response = await client.get("/health")

    assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE

    data = response.json()

    assert data["database_status"] == "offline"
    assert data["kratos_status"] == "online"
    assert "app" in data
