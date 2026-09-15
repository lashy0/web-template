from uuid import UUID

from .exceptions import PakTestNotFoundError
from .model import PakTest
from .repository import PakTestRepository


class PakTestQueries:
    def __init__(self, repository: PakTestRepository) -> None:
        self._repository = repository

    async def get(self, test_id: UUID) -> PakTest | None:
        return await self._repository.get(test_id)

    async def get_by_test_name(self, test_name: str) -> PakTest | None:
        return await self._repository.get_by_test_name(test_name)

    async def list(self, **kwargs: object) -> tuple[list[PakTest], int]:
        return await self._repository.search(**kwargs)  # type: ignore[arg-type]

    async def require(self, test_id: UUID) -> PakTest:
        item = await self.get(test_id)
        if item is None:
            raise PakTestNotFoundError
        return item
