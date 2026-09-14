from uuid import UUID

from ..model import BatchKeyGenerationJob
from ..repository import PreparationRepository


class CreateInitialPreparation:
    def __init__(self, repository: PreparationRepository) -> None:
        self._repository = repository

    async def execute(self, batch_id: UUID) -> BatchKeyGenerationJob:
        return await self._repository.create_initial_job(batch_id)
