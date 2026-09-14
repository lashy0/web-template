"""Compatibility repository name delegating to production KG persistence."""

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from app.contexts.production.kg.model import KgVersion
from app.contexts.production.kg.repository import KgRepository


class KgVersionRepository(KgRepository):
    async def get(self, version_id: UUID, *, for_update: bool = False) -> KgVersion | None:
        return await self.get_version(version_id, for_update=for_update)

    async def get_by_code(self, code: str) -> KgVersion | None:
        return await self.get_version_by_code(code)

    async def count_batches(self, version_id: UUID) -> int:
        return await self.count_batches_for_version(version_id)

    async def search(self, **kwargs: object) -> tuple[list[tuple[KgVersion, int]], int]:
        return await self.list_versions(**kwargs)  # type: ignore[arg-type]

    async def create(self, *, code: str, name: str, description: str | None) -> KgVersion:
        return await self.save_version(KgVersion(code=code, name=name, description=description))

    async def update_details(self, item: KgVersion, *, updates: Mapping[str, object]) -> KgVersion:
        for field, value in updates.items():
            setattr(item, field, value)
        return await self.save_version(item)

    async def update_archived(self, item: KgVersion, *, archived_at: datetime | None) -> KgVersion:
        item.archived_at = archived_at
        return await self.save_version(item)

    async def delete(self, item: KgVersion) -> None:
        await self.delete_version(item)
