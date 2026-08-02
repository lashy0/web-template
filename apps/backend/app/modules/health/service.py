import asyncio
from asyncio.exceptions import TimeoutError

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine


async def is_postgres_ready(engine: AsyncEngine, *, timeout: float) -> bool:
    try:
        async with asyncio.timeout(timeout):
            async with engine.begin() as conn:
                await conn.execute(select(1))
        return True
    except (TimeoutError, SQLAlchemyError):
        return False


async def is_redis_ready(client: Redis, *, timeout: float) -> bool:
    try:
        async with asyncio.timeout(timeout):
            return bool(await client.ping())
    except (TimeoutError, RedisError):
        return False
