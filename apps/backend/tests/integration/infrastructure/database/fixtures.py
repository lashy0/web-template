import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.infrastructure.database.base import Base


def _database_url(settings: Settings, *, username: str, password: str) -> URL:
    return make_url(str(settings.database_url)).set(
        username=username,
        password=password,
    )


@pytest.fixture(scope="session")
async def database_session_factory(
    test_settings: Settings,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    from app.modules.audit.models import AuditEvent  # noqa: F401
    from app.modules.users.models import User  # noqa: F401

    schema = f"test_{uuid4().hex}"
    admin_url = _database_url(
        test_settings,
        username="postgres_admin",
        password=os.environ["POSTGRES_ADMIN_PASSWORD"],
    )
    migrator_url = _database_url(
        test_settings,
        username="web_app_migrator",
        password=os.environ["POSTGRES_MIGRATOR_PASSWORD"],
    )

    admin_engine = create_async_engine(admin_url, poolclass=NullPool)
    migrator_engine = create_async_engine(
        migrator_url,
        connect_args={"options": f"-c search_path={schema}"},
        poolclass=NullPool,
    )

    try:
        async with admin_engine.begin() as connection:
            await connection.execute(
                text(f'CREATE SCHEMA "{schema}" AUTHORIZATION web_app_migrator')
            )

        async with migrator_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO web_app_runtime'))
            await connection.execute(
                text(
                    f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "{schema}" TO web_app_runtime'
                )
            )

        runtime_engine = create_async_engine(
            str(test_settings.database_url),
            connect_args={"options": f"-c search_path={schema}"},
            poolclass=NullPool,
        )
        session_factory = async_sessionmaker(
            bind=runtime_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        try:
            yield session_factory
        finally:
            await runtime_engine.dispose()
    finally:
        await migrator_engine.dispose()

        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))

        await admin_engine.dispose()


@pytest.fixture
async def db_session(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with database_session_factory() as session:
        transaction = await session.begin()

        try:
            yield session
        finally:
            await transaction.rollback()
