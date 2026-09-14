"""Compatibility repository name delegating to production KG persistence."""

from collections.abc import Mapping
from datetime import datetime

from app.contexts.production.kg.model import KgDevEuiPrefix
from app.contexts.production.kg.repository import KgRepository


class KgDevEuiPrefixRepository(KgRepository):
    async def get(self, prefix: str, *, for_update: bool = False) -> KgDevEuiPrefix | None:
        return await self.get_prefix(prefix, for_update=for_update)

    async def get_by_short_code(self, short_code: str) -> KgDevEuiPrefix | None:
        return await self.get_prefix_by_short_code(short_code)

    async def count_batches(self, prefix: str) -> int:
        return await self.count_batches_for_prefix(prefix)

    async def search(self, **kwargs: object) -> tuple[list[tuple[KgDevEuiPrefix, int]], int]:
        return await self.list_prefixes(**kwargs)  # type: ignore[arg-type]

    async def create(self, *, prefix: str, short_code: str, name: str | None) -> KgDevEuiPrefix:
        return await self.save_prefix(
            KgDevEuiPrefix(prefix=prefix, short_code=short_code, name=name)
        )

    async def update_details(
        self, item: KgDevEuiPrefix, *, updates: Mapping[str, object]
    ) -> KgDevEuiPrefix:
        for field, value in updates.items():
            setattr(item, field, value)
        return await self.save_prefix(item)

    async def update_archived(
        self, item: KgDevEuiPrefix, *, archived_at: datetime | None
    ) -> KgDevEuiPrefix:
        item.archived_at = archived_at
        return await self.save_prefix(item)

    async def delete(self, item: KgDevEuiPrefix) -> None:
        await self.delete_prefix(item)
