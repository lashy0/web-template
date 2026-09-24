from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


async def test_health(client: "AsyncClient") -> None:
    """Test health endpoint reports dependency statuses and app info."""
    response = await client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["database_status"] == "online"
    assert data["kratos_status"] == "online"
    assert data["hydra_status"] == "online"
    assert data["app"]
