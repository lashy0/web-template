from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .exceptions import PakNotFoundError
from .model import PakDevice, PakDeviceKind
from .repository import PakRepository


class PakQueries:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, pak_id: UUID) -> PakDevice | None:
        async with self._session_factory() as session:
            return await PakRepository(session).get_by_id(pak_id)

    async def require(self, repository: PakRepository, pak_id: UUID) -> PakDevice:
        pak = await repository.get_by_id(pak_id, for_update=True)
        if pak is None:
            raise PakNotFoundError
        return pak

    async def list(
        self,
        *,
        q: str | None,
        kind: PakDeviceKind | None,
        active: bool | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[PakDevice], int]:
        async with self._session_factory() as session:
            return await PakRepository(session).search(
                q=q,
                kind=kind,
                active=active,
                archived=archived,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )
