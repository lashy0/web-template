from uuid import UUID

from .exceptions import VerificationSessionNotFoundError
from .model import VerificationSession, VerificationSessionStatus, VerificationStep
from .repository import VerificationRepository


async def required_session(
    repository: VerificationRepository, session_id: UUID
) -> VerificationSession:
    item = await repository.get_session(session_id, for_update=True)
    if item is None:
        raise VerificationSessionNotFoundError
    return item


class VerificationQueries:
    def __init__(self, repository: VerificationRepository) -> None:
        self._repository = repository

    async def get(self, session_id: UUID) -> VerificationSession | None:
        return await self._repository.get_session(session_id)

    async def get_detail(
        self, session_id: UUID
    ) -> tuple[VerificationSession, list[VerificationStep]] | None:
        item = await self.get(session_id)
        return None if item is None else (item, await self._repository.list_steps(item.id))

    async def list(
        self,
        *,
        q: str | None,
        pak_id: UUID | None,
        status: VerificationSessionStatus | None,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[VerificationSession], int]:
        return await self._repository.search_sessions(
            q=q,
            pak_id=pak_id,
            status=status,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )
