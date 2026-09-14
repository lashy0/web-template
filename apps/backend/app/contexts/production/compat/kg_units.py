"""Narrow bridge for legacy KgUnit persistence while its subdomain is migrated later."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.kg.models import KgUnit
from app.modules.kg.repositories.unit import KgRepository as LegacyKgUnitRepository
from app.modules.kg.services import lifecycle


class LegacyKgUnitBridge:
    """Only the KG facts needed by production documents and batch allocation.

    KG's physical enum was intentionally reduced to REGISTERED/SCRAPPED in the
    preceding state split. Shipment membership remains the source of shipment
    reporting; this bridge must not recreate the retired PACKED/SHIPPED column.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repository = LegacyKgUnitRepository(session)

    async def create_allocated_rows(
        self, *, dev_euis: Sequence[str], short_code: str, batch_id: UUID
    ) -> int:
        return len(
            await self._repository.create_many(
                dev_euis=dev_euis, short_code=short_code, batch_id=batch_id
            )
        )

    async def get_for_shipment(self, dev_eui: str) -> KgUnit | None:
        """Lock one KG, serialising membership checks for concurrent additions."""
        return await self._repository.get_by_dev_eui(dev_eui, for_update=True)

    async def has_scrapped_for_batch(self, batch_id: UUID) -> bool:
        """Return the legacy KG fact used by batch deletion."""
        return bool(await self._repository.has_scrapped_by_batch(batch_id))

    async def delete_registered_for_batch(self, batch_id: UUID) -> None:
        """Retain legacy row locking and state validation before bulk removal."""
        units = await self._repository.list_by_batch(batch_id, for_update=True)
        for unit in units:
            lifecycle.ensure_can_delete(unit)
        await self._repository.delete_by_batch(batch_id)
