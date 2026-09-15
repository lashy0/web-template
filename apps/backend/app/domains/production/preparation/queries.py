from collections.abc import Sequence
from uuid import UUID

from .model import BatchKeyGenerationJob
from .repository import PreparationRepository


class PreparationQueries:
    def __init__(self, repository: PreparationRepository) -> None:
        self._repository = repository

    async def get(self, batch_id: UUID) -> BatchKeyGenerationJob | None:
        return await self._repository.get(batch_id)

    async def get_many(self, batch_ids: Sequence[UUID]) -> dict[UUID, BatchKeyGenerationJob]:
        return await self._repository.get_many(batch_ids)
