from __future__ import annotations

import importlib
import importlib.util
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

# Set test environment BEFORE any app imports
os.environ.update(
    {
        "LITESTAR_DEBUG": "False",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        # The task queue connects only when a job is enqueued; tests run task functions directly.
        "REDIS_URL": "redis://localhost:6379/0",
        "BACKEND_WORKERS_IN_SERVER": "False",
        "BACKEND_KRATOS_PUBLIC_URL": "http://kratos.test:4433",
        "BACKEND_KRATOS_ADMIN_URL": "http://kratos.test:4434",
        "BACKEND_HYDRA_PUBLIC_URL": "http://hydra.test:4444",
        "BACKEND_HYDRA_ADMIN_URL": "http://hydra.test:4445",
        "BACKEND_PAK_ACCESS_KEY_ENCRYPTION_KEY": "8VmFOM9tWG6LbUOfXkxRYnyrl7I0K8VXcYz0aSlBryM=",
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
    "pytest_databases.docker",
    "pytest_databases.docker.postgres",
]

pytestmark = pytest.mark.anyio


@dataclass(frozen=True, slots=True)
class KratosService:
    """Addresses of the isolated Kratos instance used by integration tests."""

    admin_url: str
    public_url: str


@dataclass(frozen=True, slots=True)
class HydraService:
    """Addresses of the isolated Hydra instance used by integration tests."""

    admin_url: str
    public_url: str


TEST_CONTAINER_LABEL = "pytest_databases"
"""pytest-databases removes the containers with this label when a test run starts and when it ends."""

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _shared_tmp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return a directory shared by all xdist workers of the run, as pytest-databases does."""
    base = tmp_path_factory.getbasetemp()

    return base.parent if os.environ.get("PYTEST_XDIST_WORKER") else base


def _published_port(container: Container, port: str) -> int:
    """Return the host port Docker assigned to a published container port."""
    bindings: list[dict[str, str]] | None = container.ports.get(port)

    if not bindings:
        msg = f"Container port {port} is not published."
        raise RuntimeError(msg)

    return int(bindings[0]["HostPort"])


def _ensure_database(postgres_service: PostgresService, name: str) -> None:
    """Create a database next to the test databases unless it already exists.

    Kratos and Hydra both own tables such as ``networks``; each needs its own
    database or whichever migrates second fails.
    """
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    conninfo = make_conninfo(
        host=postgres_service.host,
        port=postgres_service.port,
        user=postgres_service.user,
        password=postgres_service.password,
        dbname=postgres_service.database,
    )

    with psycopg.connect(conninfo, autocommit=True) as connection:
        exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()

        if exists is None:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def _ory_dsn(postgres_service: PostgresService, database: str) -> str:
    """DSN for an Ory container reaching the host's test PostgreSQL."""
    return (
        "postgres://"
        f"{postgres_service.user}:{postgres_service.password}"
        f"@host.docker.internal:{postgres_service.port}/{database}"
        "?sslmode=disable"
    )


def _provide_ory_service(
    postgres_service: PostgresService,
    lock_dir: Path,
    *,
    service: str,
    image: str,
    serve_command: list[str],
    public_port: str,
    admin_port: str,
    environment: dict[str, str],
) -> tuple[str, str]:
    """Start one container of an Ory service for the whole run, or reuse the running one.

    All xdist workers share the container, as they share the PostgreSQL
    container of pytest-databases; its data outlives each test, so tests use
    unique identifiers. The container carries the pytest-databases label and
    is removed as soon as it stops, so pytest-databases removes it at the end
    of the run, and at the start of the next one if a run was killed.

    Returns the admin and the public URL.
    """
    from docker import DockerClient
    from filelock import FileLock

    client = DockerClient.from_env()
    name = f"pytest_databases_backend_{service}"
    database = f"backend_tests_{service}"
    config = f"/etc/config/{service}/{service}.yaml"
    config_dir = _REPOSITORY_ROOT / "infrastructure" / "identity" / service

    def run(command: list[str], *, container_name: str | None = None, ports: list[str] | None = None) -> Container:
        return client.containers.run(
            image,
            command=[*command, "--config", config],
            detach=True,
            remove=True,
            labels=[TEST_CONTAINER_LABEL],
            name=container_name,
            ports=dict.fromkeys(ports or ()),
            environment={**environment, "DSN": _ory_dsn(postgres_service, database), "SQA_OPT_OUT": "true"},
            volumes={str(config_dir): {"bind": f"/etc/config/{service}", "mode": "ro"}},
            extra_hosts={"host.docker.internal": "host-gateway"},
        )

    with FileLock(lock_dir / f"{name}.lock"):
        running = [item for item in client.containers.list(filters={"name": name}) if item.name == name]

        if running:
            container = running[0]
        else:
            _ensure_database(postgres_service, database)
            result = run(["migrate", "sql", "-e", "--yes"]).wait(timeout=120)

            if result["StatusCode"] != 0:
                msg = f"{service} database migration failed with status {result['StatusCode']}."
                raise RuntimeError(msg)

            container = run(serve_command, container_name=name, ports=[public_port, admin_port])
            container.reload()
            _wait_until_ready(container, f"http://127.0.0.1:{_published_port(container, admin_port)}", service)

    return (
        f"http://127.0.0.1:{_published_port(container, admin_port)}",
        f"http://127.0.0.1:{_published_port(container, public_port)}",
    )


def _wait_until_ready(container: Container, admin_url: str, service: str) -> None:
    deadline = monotonic() + 90

    while monotonic() < deadline:
        try:
            with urlopen(f"{admin_url}/health/ready", timeout=1) as response:
                if response.status == 200:
                    return
        except (HTTPError, OSError, URLError):
            sleep(0.5)

    logs = container.logs().decode(errors="replace")
    msg = f"{service} did not become ready:\n{logs}"
    raise RuntimeError(msg)


@contextmanager
def _environment(**values: str) -> Generator[None]:
    """Set environment variables for the application settings and restore them afterwards."""
    from app.config.settings import get_settings

    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    get_settings.cache_clear()

    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.fixture(scope="session")
def postgres_image() -> str:
    """Test on the PostgreSQL image of ``infrastructure/database/docker-compose.yaml``, not the pytest-databases default."""
    return "postgres:17-trixie"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def anyio_backend_options() -> dict[str, bool]:
    """Prefer uvloop when available for AnyIO's asyncio backend."""
    if importlib.util.find_spec("uvloop") is None:
        return {}

    return {"use_uvloop": True}


@pytest.fixture(name="kratos_service", scope="session")
def fx_kratos_service(
    postgres_service: PostgresService,
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[KratosService]:
    """The Kratos instance of the test run, backed by its own test PostgreSQL database."""
    admin_url, public_url = _provide_ory_service(
        postgres_service,
        _shared_tmp_path(tmp_path_factory),
        service="kratos",
        image="oryd/kratos:v26.2.0",
        serve_command=["serve", "--sqa-opt-out"],
        public_port="4433/tcp",
        admin_port="4434/tcp",
        environment={
            "SECRETS_COOKIE": "a" * 64,
            "SECRETS_CIPHER": "b" * 32,
        },
    )

    with _environment(BACKEND_KRATOS_ADMIN_URL=admin_url, BACKEND_KRATOS_PUBLIC_URL=public_url):
        yield KratosService(admin_url=admin_url, public_url=public_url)


@pytest.fixture(name="hydra_service", scope="session")
def fx_hydra_service(
    postgres_service: PostgresService,
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[HydraService]:
    """The Hydra instance of the test run, backed by its own test PostgreSQL database."""
    admin_url, public_url = _provide_ory_service(
        postgres_service,
        _shared_tmp_path(tmp_path_factory),
        service="hydra",
        image="oryd/hydra:v26.2.0",
        serve_command=["serve", "all", "--dev", "--sqa-opt-out"],
        public_port="4444/tcp",
        admin_port="4445/tcp",
        environment={
            "SECRETS_SYSTEM": "c" * 32,
            "URLS_SELF_ISSUER": "http://hydra.test",
        },
    )

    with _environment(BACKEND_HYDRA_ADMIN_URL=admin_url, BACKEND_HYDRA_PUBLIC_URL=public_url):
        yield HydraService(admin_url=admin_url, public_url=public_url)


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

    from app.config.settings import get_settings

    get_settings.cache_clear()

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
def fx_sessionmaker(engine: AsyncEngine, db_schema: None) -> async_sessionmaker[AsyncSession]:
    """Create sessionmaker factory bound to the test engine, with the tables in place."""
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
