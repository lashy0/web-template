from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import Role

from .models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        *,
        user_id: UUID | None = None,
        identity_id: UUID,
        name: str,
        role: Role,
        identity_login: str | None = None,
        auth_state: str = "inactive",
        synced_at: datetime | None = None,
    ) -> User:
        user = User(
            id=user_id or uuid4(),
            identity_id=identity_id,
            name=name,
            role=role,
            identity_login=identity_login,
            auth_state=auth_state,
            auth_state_synced_at=synced_at,
        )

        self._session.add(user)

        await self._session.flush()
        await self._session.refresh(user)

        return user

    async def get_by_id(
        self,
        user_id: UUID,
        *,
        for_update: bool = False,
    ) -> User | None:
        return await self._session.get(
            User,
            user_id,
            with_for_update=for_update,
            populate_existing=for_update,
        )

    async def get_by_identity_id(self, identity_id: UUID) -> User | None:
        statement = select(User).where(User.identity_id == identity_id)

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def update_name(
        self,
        user: User,
        *,
        name: str,
    ) -> User:
        user.name = name

        await self._session.flush()
        await self._session.refresh(user)

        return user

    async def update_role(
        self,
        user: User,
        *,
        role: Role,
    ) -> User:
        user.role = role

        await self._session.flush()
        await self._session.refresh(user)

        return user

    async def update_identity_projection(
        self,
        user: User,
        *,
        login: str | None,
        state: str,
        synced_at: datetime,
    ) -> User:
        user.identity_login = login
        user.auth_state = state
        user.auth_state_synced_at = synced_at

        await self._session.flush()
        await self._session.refresh(user)

        return user

    async def update_archived(
        self,
        user: User,
        *,
        archived_at: datetime | None,
    ) -> User:
        user.archived_at = archived_at

        await self._session.flush()
        await self._session.refresh(user)

        return user

    async def delete(self, user: User) -> None:
        await self._session.delete(user)
        await self._session.flush()

    async def delete_if_exists(self, user_id: UUID) -> None:
        await self._session.execute(delete(User).where(User.id == user_id))

    async def search(
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
        filters: list[ColumnElement[bool]] = [
            User.archived_at.is_not(None) if archived else User.archived_at.is_(None)
        ]

        if q:
            pattern = f"%{q}%"
            filters.append(or_(User.name.ilike(pattern), User.identity_login.ilike(pattern)))

        if role is not None:
            filters.append(User.role == role)

        if auth_state is not None:
            filters.append(User.auth_state == auth_state)

        statement = select(User).where(*filters)

        column = {
            "name": User.name,
            "login": User.identity_login,
            "created_at": User.created_at,
            "archived_at": User.archived_at,
        }[sort]

        sorted_column = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()
        statement = statement.order_by(sorted_column, User.id.asc())
        statement = statement.offset((page - 1) * page_size).limit(page_size)
        count = await self._session.scalar(select(func.count()).select_from(User).where(*filters))
        result = await self._session.execute(statement)

        return list(result.scalars()), int(count or 0)

    async def list_all(self) -> list[User]:
        result = await self._session.execute(select(User))

        return list(result.scalars())

    async def get_for_reconciliation(self, user_id: UUID, version: int) -> User | None:
        # Never queue behind an API operation holding this user's row across Kratos I/O.
        user: User | None = await self._session.scalar(
            select(User)
            .where(User.id == user_id, User.version == version)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        return user

    async def reconcile_projection(
        self, user: User, *, login: str | None, state: str, synced_at: datetime
    ) -> bool:
        # Explicit SQL bypasses ORM versioning, so compare and increment here as well.
        result = await self._session.scalar(
            update(User)
            .where(User.id == user.id, User.version == user.version)
            .values(
                identity_login=login,
                auth_state=state,
                auth_state_synced_at=synced_at,
                version=User.version + 1,
            )
            .returning(User.id)
            .execution_options(synchronize_session=False)
        )

        if result is None:
            return False

        await self._session.refresh(user)

        return True

    async def count(self) -> int:
        result = await self._session.scalar(select(func.count()).select_from(User))

        return int(result or 0)
