from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .model import PakTest
from .queries import PakTestQueries
from .repository import PakTestRepository


class PakTestCatalog:
    """Read model used by the stable /pak/tests API route."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, test_id: UUID) -> PakTest | None:
        async with self._session_factory() as session:
            return await PakTestQueries(PakTestRepository(session)).get(test_id)

    async def list(self, **kwargs: object) -> tuple[list[PakTest], int]:
        async with self._session_factory() as session:
            return await PakTestQueries(PakTestRepository(session)).list(**kwargs)
