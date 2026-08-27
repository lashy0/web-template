from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pak.models import PakDevice, PakDeviceKind


class PakRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        *,
        pak_id: UUID | None = None,
        code: str,
        kind: PakDeviceKind,
        oauth_client_id: str,
        encrypted_access_key: str,
        active: bool = True,
    ) -> PakDevice:
        pak = PakDevice(
            id=pak_id or uuid4(),
            code=code,
            kind=kind,
            oauth_client_id=oauth_client_id,
            encrypted_access_key=encrypted_access_key,
            is_active=active,
        )

        self._session.add(pak)
        await self._session.flush()
        await self._session.refresh(pak)

        return pak

    async def get_by_id(self, pak_id: UUID) -> PakDevice | None:
        return await self._session.get(PakDevice, pak_id)

    async def get_by_code(self, code: str) -> PakDevice | None:
        statement = select(PakDevice).where(
            PakDevice.code == code
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_oauth_client_id(self, oauth_client_id: str) -> PakDevice | None:
        statement = select(PakDevice).where(
            PakDevice.oauth_client_id == oauth_client_id
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def update_details(
        self,
        pak: PakDevice,
        *,
        code: str | None = None,
        kind: PakDeviceKind | None = None,
    ) -> PakDevice:
        if code is not None:
            pak.code = code

        if kind is not None:
            pak.kind = kind

        await self._session.flush()
        await self._session.refresh(pak)

        return pak

    async def update_active(
        self,
        pak: PakDevice,
        *,
        active: bool,
    ) -> PakDevice:
        pak.is_active = active

        await self._session.flush()
        await self._session.refresh(pak)

        return pak

    async def update_access_key(
        self,
        pak: PakDevice,
        *,
        encrypted_access_key: str,
    ) -> PakDevice:
        pak.encrypted_access_key = encrypted_access_key

        await self._session.flush()
        await self._session.refresh(pak)

        return pak

    async def update_archived(
        self,
        pak: PakDevice,
        *,
        archived_at: datetime | None,
    ) -> PakDevice:
        pak.archived_at = archived_at

        await self._session.flush()
        await self._session.refresh(pak)

        return pak

    async def update_last_seen(
        self,
        pak: PakDevice,
        *,
        last_seen_at: datetime | None,
    ) -> PakDevice:
        pak.last_seen_at = last_seen_at

        await self._session.flush()
        await self._session.refresh(pak)

        return pak

    async def delete(self, pak: PakDevice) -> None:
        await self._session.delete(pak)
        await self._session.flush()

    async def search(
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
        filters: list[ColumnElement[bool]] = [
            PakDevice.archived_at.is_not(None) if archived else PakDevice.archived_at.is_(None)
        ]

        if q:
            pattern = f"%{q}%"
            filters.append(
                or_(
                    PakDevice.code.ilike(pattern),
                    PakDevice.oauth_client_id.ilike(pattern),
                )
            )

        if kind is not None:
            filters.append(PakDevice.kind == kind)

        if active is not None:
            filters.append(PakDevice.is_active == active)

        statement = select(PakDevice).where(*filters)

        column = {
            "code": PakDevice.code,
            "kind": PakDevice.kind,
            "created_at": PakDevice.created_at,
            "updated_at": PakDevice.updated_at,
            "last_seen_at": PakDevice.last_seen_at,
            "archived_at": PakDevice.archived_at,
        }[sort]

        sorted_column = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()
        statement = statement.order_by(sorted_column, PakDevice.id.asc())
        statement = statement.offset((page - 1) * page_size).limit(page_size)
        count = await self._session.scalar(select(func.count()).select_from(PakDevice).where(*filters))
        result = await self._session.execute(statement)

        return list(result.scalars()), int(count or 0)
