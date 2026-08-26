from collections.abc import AsyncGenerator
from typing import Annotated, cast

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import Database


async def get_database(request: Request) -> Database:
    try:
        return cast(Database, request.app.state.database)
    except AttributeError as exc:
        raise RuntimeError(
            "Database is not initialized. Application lifespan was probably not started."
        ) from exc


DatabaseDep = Annotated[Database, Depends(get_database)]


async def get_session(
    database: DatabaseDep,
) -> AsyncGenerator[AsyncSession]:
    async with database.session_factory() as session:
        yield session


SessionDep = Annotated[
    AsyncSession,
    Depends(get_session),
]


async def get_redis(request: Request) -> Redis:
    try:
        return cast(Redis, request.app.state.redis)
    except AttributeError as exc:
        raise RuntimeError(
            "Redis is not initialized. Application lifespan was probably not started."
        ) from exc


RedisDep = Annotated[
    Redis,
    Depends(get_redis),
]
