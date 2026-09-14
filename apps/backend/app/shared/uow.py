"""Small transaction boundary for new command runners.

This helper deliberately owns only the session lifecycle and ``session.begin()``.
Repositories, commands, and audit writers receive the yielded session and never
commit or roll back it themselves.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@asynccontextmanager
async def transaction(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield one mutable-operation session and commit on successful exit."""
    async with session_factory() as session, session.begin():
        yield session
