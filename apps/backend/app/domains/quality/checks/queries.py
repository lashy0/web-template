from uuid import UUID

from .exceptions import CheckNotFoundError
from .model import Check
from .repository import CheckRepository


class CheckQueries:
    def __init__(self, repository: CheckRepository) -> None:
        self._repository = repository

    async def get(self, test_id: UUID) -> Check | None:
        return await self._repository.get(test_id)

    async def get_by_test_name(self, test_name: str) -> Check | None:
        return await self._repository.get_by_test_name(test_name)

    async def list(self, **kwargs: object) -> tuple[list[Check], int]:
        return await self._repository.search(**kwargs)  # type: ignore[arg-type]

    async def require(self, test_id: UUID) -> Check:
        item = await self.get(test_id)
        if item is None:
            raise CheckNotFoundError
        return item
