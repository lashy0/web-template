from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir
from time import monotonic, sleep
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

# Set test environment BEFORE any app imports
os.environ.update(
    {
        "LITESTAR_DEBUG": "False",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "BACKEND_KRATOS_PUBLIC_URL": "http://kratos.test:4433",
        "BACKEND_KRATOS_ADMIN_URL": "http://kratos.test:4434",
    }
)

import pytest
from advanced_alchemy.base import UUIDv7AuditBase
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from docker.models.containers import Container
    from pytest_databases.docker.postgres import PostgresService
    from sqlalchemy.ext.asyncio import AsyncEngine


pytest_plugins = [
    "tests.data_fixtures",
    "pytest_databases.docker",
    "pytest_databases.docker.postgres",
]

pytestmark = pytest.mark.anyio


@dataclass(frozen=True, slots=True)
class KratosService:
    """Addresses of the isolated Kratos instance used by integration tests."""

    admin_url: str
    public_url: str


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def anyio_backend_options() -> dict[str, bool]:
    """Prefer uvloop when available for AnyIO's asyncio backend."""
    try:
        import uvloop  # noqa: F401
    except ImportError:
        return {}

    return {"use_uvloop": True}


@pytest.fixture(name="kratos_service", scope="session")
def fx_kratos_service(postgres_service: PostgresService) -> Generator[KratosService]:
    """Start an isolated Kratos instance backed by the test PostgreSQL database."""
    from docker import DockerClient
    from docker.errors import APIError
    from filelock import FileLock

    kratos_config_dir = Path(__file__).resolve().parents[3] / "infrastructure" / "identity" / "kratos"
    dsn = (
        "postgres://"
        f"{postgres_service.user}:{postgres_service.password}"
        f"@host.docker.internal:{postgres_service.port}/{postgres_service.database}"
        "?sslmode=disable"
    )
    environment = {
        "DSN": dsn,
        "SQA_OPT_OUT": "true",
        "SECRETS_COOKIE": "a" * 64,
        "SECRETS_CIPHER": "b" * 32,
    }
    volumes = {
        str(kratos_config_dir): {
            "bind": "/etc/config/kratos",
            "mode": "ro",
        }
    }
    client = DockerClient.from_env()
    image = "oryd/kratos:v26.2.0"

    with FileLock(Path(gettempdir()) / "backend-kratos-migrations.lock"):
        migration = client.containers.run(
            image,
            command=["migrate", "sql", "-e", "--yes", "--config", "/etc/config/kratos/kratos.yaml"],
            detach=True,
            remove=True,
            environment=environment,
            volumes=volumes,
            extra_hosts={"host.docker.internal": "host-gateway"},
        )
        result = migration.wait(timeout=120)

        if result["StatusCode"] != 0:
            logs = migration.logs().decode(errors="replace")
            msg = f"Kratos database migration failed:\n{logs}"
            raise RuntimeError(msg)

    container: Container = client.containers.run(
        image,
        command=["serve", "--sqa-opt-out", "--config", "/etc/config/kratos/kratos.yaml"],
        detach=True,
        environment=environment,
        ports={"4433/tcp": None, "4434/tcp": None},
        volumes=volumes,
        extra_hosts={"host.docker.internal": "host-gateway"},
    )

    previous_admin_url = os.environ.get("BACKEND_KRATOS_ADMIN_URL")
    previous_public_url = os.environ.get("BACKEND_KRATOS_PUBLIC_URL")

    try:
        container.reload()
        public_port = int(container.ports["4433/tcp"][0]["HostPort"])
        admin_port = int(container.ports["4434/tcp"][0]["HostPort"])
        service = KratosService(
            admin_url=f"http://127.0.0.1:{admin_port}",
            public_url=f"http://127.0.0.1:{public_port}",
        )
        deadline = monotonic() + 90

        while monotonic() < deadline:
            try:
                with urlopen(f"{service.admin_url}/health/ready", timeout=1) as response:
                    if response.status == 200:
                        break
            except (HTTPError, OSError, URLError):
                sleep(0.5)
        else:
            logs = container.logs().decode(errors="replace")
            msg = f"Kratos did not become ready:\n{logs}"
            raise RuntimeError(msg)

        os.environ["BACKEND_KRATOS_ADMIN_URL"] = service.admin_url
        os.environ["BACKEND_KRATOS_PUBLIC_URL"] = service.public_url

        import app.config
        from app.config.settings import get_settings

        get_settings.cache_clear()
        importlib.reload(app.config)

        yield service

    finally:
        if previous_admin_url is None:
            os.environ.pop("BACKEND_KRATOS_ADMIN_URL", None)
        else:
            os.environ["BACKEND_KRATOS_ADMIN_URL"] = previous_admin_url

        if previous_public_url is None:
            os.environ.pop("BACKEND_KRATOS_PUBLIC_URL", None)
        else:
            os.environ["BACKEND_KRATOS_PUBLIC_URL"] = previous_public_url

        try:
            container.remove(force=True)
        except APIError:
            pass


@pytest.fixture(name="engine", scope="session")
def fx_engine(postgres_service: PostgresService) -> Generator[AsyncEngine]:
    """PostgreSQL instance for testing.

    Uses asyncpg driver (native async) instead of psycopg (greenlet-based)
    to avoid MissingGreenlet errors in tests.

    Note: This is a sync fixture that yields an async engine. The engine creation
    and disposal are sync operations, but engine usage is async.

    Returns:
        Async SQLAlchemy engine instance.
    """
    import asyncio

    # Set DATABASE_URL for the app to use
    db_url = URL(
        drivername="postgresql+asyncpg",
        username=postgres_service.user,
        password=postgres_service.password,
        host=postgres_service.host,
        port=postgres_service.port,
        database=postgres_service.database,
        query={},  # type: ignore[arg-type]
    )

    os.environ["DATABASE_URL"] = db_url.render_as_string(hide_password=False)

    import importlib

    import app.config
    from app.config.settings import get_settings

    get_settings.cache_clear()
    importlib.reload(app.config)

    engine = create_async_engine(
        db_url,
        echo=False,
        poolclass=NullPool,
    )

    yield engine

    loop = asyncio.new_event_loop()

    try:
        loop.run_until_complete(engine.dispose())
    finally:
        loop.close()


@pytest.fixture(name="sessionmaker", scope="session")
def fx_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create sessionmaker factory bound to the test engine."""
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


@pytest.fixture(name="db_schema", scope="session")
def fx_db_schema(engine: AsyncEngine) -> Generator[None]:
    """Create schema once per test session.

    Note: Schema is created once and not dropped until session ends.
    Individual tests use db_cleanup for per-test isolation.
    """
    import asyncio

    async def create_schema() -> None:
        metadata = UUIDv7AuditBase.registry.metadata

        async with engine.begin() as connection:
            await connection.run_sync(metadata.create_all)

    async def drop_schema() -> None:
        metadata = UUIDv7AuditBase.registry.metadata

        async with engine.begin() as connection:
            await connection.run_sync(metadata.drop_all)

    loop = asyncio.new_event_loop()

    try:
        loop.run_until_complete(create_schema())

        yield

        loop.run_until_complete(drop_schema())
    finally:
        loop.close()


@pytest.fixture(name="db_cleanup")
async def fx_db_cleanup(engine: AsyncEngine, db_schema: None) -> AsyncGenerator[None]:
    """Per-test database cleanup for isolation.

    Truncates all tables before each test to ensure clean state.
    This is faster than drop/create but still provides isolation.
    """
    yield

    # Clean up after test
    metadata = UUIDv7AuditBase.registry.metadata

    async with engine.begin() as connection:
        for table in reversed(metadata.sorted_tables):
            await connection.execute(table.delete())


@pytest.fixture(name="session")
async def fx_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    db_cleanup: None,
) -> AsyncGenerator[AsyncSession]:
    """Create database session for tests with cleanup.

    Uses sessionmaker pattern which properly handles greenlet context
    for async psycopg driver.
    """
    async with sessionmaker() as session:
        yield session
