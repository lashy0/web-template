"""FastAPI dependencies shared by HTTP adapters without coupling domains to ``app.api``."""

from collections.abc import AsyncGenerator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database.session import Database


async def get_database(request: Request) -> Database:
    try:
        return cast(Database, request.app.state.database)
    except AttributeError as exc:
        raise RuntimeError(
            "Database is not initialized. Application lifespan was probably not started."
        ) from exc


DatabaseDep = Annotated[Database, Depends(get_database)]


async def get_session_factory(database: DatabaseDep) -> async_sessionmaker[AsyncSession]:
    """Return the application session factory without exposing ``app.state`` to routers."""
    return database.session_factory


SessionFactoryDep = Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)]


async def get_session(database: DatabaseDep) -> AsyncGenerator[AsyncSession]:
    async with database.session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
