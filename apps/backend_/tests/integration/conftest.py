from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from litestar.testing import AsyncTestClient

from app import config
from app.domain.accounts.schemas import UserCreate
from app.domain.accounts.services import UserService
from app.lib.kratos import KratosClient

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator

    from httpx import AsyncClient
    from litestar import Litestar
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

    from tests.conftest import KratosService


pytestmark = pytest.mark.anyio


@pytest.fixture(name="kratos_client")
def fx_kratos_client(kratos_service: KratosService) -> KratosClient:
    """Kratos Admin API client bound to the isolated test instance."""
    return KratosClient(base_url=kratos_service.admin_url)


@pytest.fixture
def _patch_db(
    app: Litestar,
    engine: AsyncEngine,
    sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch the database connection for HTTP client tests.

    This fixture ensures that all HTTP requests made through the test client
    use the same test database that fixtures populate.

    Note: This is NOT autouse - only client tests need it.
    Service tests use session directly and don't need app patching.
    """

    monkeypatch.setattr(config.alchemy, "session_maker", sessionmaker)
    monkeypatch.setattr(config.alchemy, "engine_instance", engine)

    # Also patch app state for tests that check app.state directly
    app.state[config.alchemy.engine_app_state_key] = engine
    app.state[config.alchemy.session_maker_app_state_key] = sessionmaker


@pytest.fixture
async def seeded_db(
    sessionmaker: async_sessionmaker[AsyncSession],
    raw_users: list[dict[str, Any]],
    kratos_client: KratosClient,
    db_cleanup: None,
) -> AsyncGenerator[None]:
    """Populate PostgreSQL and Kratos with standard users when requested.

    Args:
        sessionmaker: The SQLAlchemy sessionmaker factory.
        raw_users: Test users to create in both systems.
        kratos_client: Client for the isolated Kratos Admin API.
        db_cleanup: Per-test database isolation fixture.
    """
    async with sessionmaker() as session:
        users_service = UserService(session=session)

        for raw_user in raw_users:
            user = await users_service.create_user(
                UserCreate(
                    login=raw_user["login"],
                    name=raw_user["name"],
                    password=raw_user["password"],
                    role=raw_user["role"],
                    is_active=raw_user["is_active"],
                ),
                kratos=kratos_client,
            )

            if raw_user["archived"]:
                await users_service.set_archived(
                    user.id,
                    archived=True,
                    kratos=kratos_client,
                )

    yield


@pytest.fixture(name="client")
async def fx_client(
    app: Litestar,
    _patch_db: None,
    db_cleanup: None,
) -> AsyncIterator[AsyncClient]:
    """Async client that calls requests on the app."""
    async with AsyncTestClient(app) as client:
        yield client


@pytest.fixture(name="seeded_client")
async def fx_seeded_client(
    app: Litestar,
    _patch_db: None,
    seeded_db: None,
    db_cleanup: None,
) -> AsyncIterator[AsyncClient]:
    """Async client with seeded database.

    Uses _patch_db to ensure the test client uses the same database
    that was seeded with fixtures.
    """
    async with AsyncTestClient(app=app) as client:
        yield client
