import asyncio
from logging.config import fileConfig

from pydantic import ValidationError
from pydantic_settings import SettingsError
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context, util
from app.core.config import get_settings
from app.infrastructure.database import models  # noqa: F401
from app.infrastructure.database.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Return the migration database URL from application settings.

    Returns:
        The asynchronous SQLAlchemy URL with schema migration privileges.
    """
    try:
        settings = get_settings()
        return str(settings.migration_database_url)
    except (SettingsError, ValidationError, ValueError) as error:
        raise util.CommandError(f"Invalid backend configuration:\n{error}") from None


config.set_main_option(
    "sqlalchemy.url",
    get_database_url().replace("%", "%%"),
)


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection.

    Offline mode configures Alembic using only the database URL. It is useful
    for generating SQL scripts with the ``--sql`` option.

    SQL statements are written to the configured output instead of being
    executed against the database.
    """
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure and run migrations using a synchronous connection.

    Alembic operates through SQLAlchemy's synchronous migration API.
    SQLAlchemy provides this synchronous connection from the asynchronous
    connection by using ``AsyncConnection.run_sync()``.

    Args:
        connection: The synchronous SQLAlchemy connection used by Alembic.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an asynchronous engine and run Alembic migrations.

    The engine is created from the active Alembic configuration. A null pool
    is used because migration commands are short-lived processes and do not
    need persistent pooled connections.
    """
    configuration = config.get_section(
        config.config_ini_section,
        {},
    )

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations against an active database connection.

    Alembic itself exposes a synchronous migration API. The asynchronous
    migration coroutine is therefore started through ``asyncio.run()``.
    """
    asyncio.run(
        run_async_migrations(),
        loop_factory=asyncio.SelectorEventLoop,
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
