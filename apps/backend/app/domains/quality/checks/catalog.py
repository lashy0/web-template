from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .model import Check
from .queries import CheckQueries
from .repository import CheckRepository


class CheckCatalog:
    """Read model used by the stable /pak/tests API route."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, test_id: UUID) -> Check | None:
        async with self._session_factory() as session:
            return await CheckQueries(CheckRepository(session)).get(test_id)

    async def list(self, **kwargs: object) -> tuple[list[Check], int]:
        async with self._session_factory() as session:
            return await CheckQueries(CheckRepository(session)).list(**kwargs)
