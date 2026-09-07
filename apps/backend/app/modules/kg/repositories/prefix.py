from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import KgDevEuiPrefix


class KgDevEuiPrefixRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self,
        prefix: str,
        *,
        for_update: bool = False,
    ) -> KgDevEuiPrefix | None:
        return await self._session.get(
            KgDevEuiPrefix,
            prefix,
            with_for_update=for_update,
            populate_existing=for_update,
        )

    async def get_by_short_code(self, short_code: str) -> KgDevEuiPrefix | None:
        result = await self._session.scalars(
            select(KgDevEuiPrefix).where(KgDevEuiPrefix.short_code == short_code).limit(1)
        )

        return result.first()

    async def list(self) -> list[KgDevEuiPrefix]:
        result = await self._session.scalars(
            select(KgDevEuiPrefix).order_by(KgDevEuiPrefix.prefix.asc())
        )

        return list(result)

    async def create(
        self,
        *,
        prefix: str,
        short_code: str,
        name: str | None,
    ) -> KgDevEuiPrefix:
        item = KgDevEuiPrefix(
            prefix=prefix,
            short_code=short_code,
            name=name,
        )

        self._session.add(item)

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def update_details(
        self,
        item: KgDevEuiPrefix,
        *,
        updates: Mapping[str, object],
    ) -> KgDevEuiPrefix:
        for field, value in updates.items():
            setattr(item, field, value)

        await self._session.flush()
        await self._session.refresh(item)

        return item

    async def delete(self, item: KgDevEuiPrefix) -> None:
        await self._session.delete(item)
        await self._session.flush()
