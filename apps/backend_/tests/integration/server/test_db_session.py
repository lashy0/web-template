"""Request handlers get a database session bound to the configured engine."""

from typing import TYPE_CHECKING

import pytest
from litestar import get
from litestar.di import NamedDependency
from litestar.testing import AsyncTestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

if TYPE_CHECKING:
    from litestar import Litestar

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


async def test_db_session_dependency(app: "Litestar", engine: AsyncEngine, _patch_db: None) -> None:
    """Test that handlers receive session attached to patched engine.

    Note: _patch_db fixture ensures the app uses the test database engine.
    """

    @get("/db-session-test", opt={"exclude_from_auth": True})
    async def db_session_dependency_patched(db_session: NamedDependency[AsyncSession]) -> dict[str, str]:
        return {"result": f"{db_session.bind is engine = }"}

    app.register(db_session_dependency_patched)

    async with AsyncTestClient(app) as client:
        response = await client.get("/db-session-test")

    assert response.json()["result"] == "db_session.bind is engine = True"
