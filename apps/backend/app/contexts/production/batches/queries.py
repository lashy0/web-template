from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.modules.batch.exceptions import BatchInvalidFiltersError, BatchNotFoundError
from app.modules.batch.models import BatchKeyGenerationJob

from .model import Batch, BatchStatus
from .repository import BatchRepository


class PreparationReadApi(Protocol):
    async def get(self, batch_id: UUID) -> BatchKeyGenerationJob | None: ...

    async def get_many(self, batch_ids: Sequence[UUID]) -> dict[UUID, BatchKeyGenerationJob]: ...


class BatchQueries:
    def __init__(self, repository: BatchRepository, preparation: PreparationReadApi) -> None:
        self._repository = repository
        self._preparation = preparation

    async def get(self, batch_id: UUID) -> Batch | None:
        return await self._repository.get(batch_id)

    async def list(
        self,
        *,
        q: str | None,
        status: BatchStatus | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
        production_order_id: UUID | None = None,
        without_production_order: bool = False,
    ) -> tuple[list[Batch], int]:
        if production_order_id is not None and without_production_order:
            raise BatchInvalidFiltersError
        return await self._repository.search(
            q=q,
            status=status,
            archived=archived,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
            production_order_id=production_order_id,
            without_production_order=without_production_order,
        )

    async def get_preparation_job(self, batch_id: UUID) -> BatchKeyGenerationJob | None:
        return await self._preparation.get(batch_id)

    async def get_preparation_jobs(
        self, batch_ids: Sequence[UUID]
    ) -> dict[UUID, BatchKeyGenerationJob]:
        return await self._preparation.get_many(batch_ids)


async def required_batch(
    repository: BatchRepository, batch_id: UUID, *, for_update: bool = False
) -> Batch:
    batch = await repository.get(batch_id, for_update=for_update)
    if batch is None:
        raise BatchNotFoundError
    return batch
