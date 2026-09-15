from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.security import Role

from .exceptions import UserNotFoundError
from .model import User
from .repository import UserRepository


class UserQueries:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, user_id: UUID) -> User | None:
        async with self._session_factory() as session:
            return await UserRepository(session).get_by_id(user_id)

    async def get_by_identity_id(self, identity_id: UUID) -> User | None:
        async with self._session_factory() as session:
            return await UserRepository(session).get_by_identity_id(identity_id)

    async def list(
        self,
        *,
        q: str | None,
        role: Role | None,
        auth_state: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[User], int]:
        async with self._session_factory() as session:
            return await UserRepository(session).search(
                q=q,
                role=role,
                auth_state=auth_state,
                archived=archived,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )


async def required_user(
    repository: UserRepository, user_id: UUID, *, for_update: bool = True
) -> User:
    user = await repository.get_by_id(user_id, for_update=for_update)
    if user is None:
        raise UserNotFoundError
    return user
