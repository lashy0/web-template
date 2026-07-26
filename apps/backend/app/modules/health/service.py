import asyncio
from asyncio.exceptions import TimeoutError

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine


async def is_postgres_ready(engine: AsyncEngine, timeout: float = 2.0) -> bool:
    try:
        async with asyncio.timeout(timeout):
            async with engine.begin() as conn:
                await conn.execute(select(1))
        return True
    except (TimeoutError, SQLAlchemyError):
        return False
