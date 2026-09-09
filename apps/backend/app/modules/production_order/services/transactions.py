from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..exceptions import ProductionOrderConflictError


@asynccontextmanager
async def transaction(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    try:
        async with factory() as session, session.begin():
            yield session

    except IntegrityError as exc:
        raise ProductionOrderConflictError from exc
