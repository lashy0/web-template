from typing import Annotated, cast

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.shared.dependencies import (
    DatabaseDep,
    SessionDep,
    SessionFactoryDep,
    get_database,
    get_session,
    get_session_factory,
)

__all__ = [
    "DatabaseDep",
    "RedisDep",
    "SessionDep",
    "SessionFactoryDep",
    "get_database",
    "get_redis",
    "get_session",
    "get_session_factory",
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
