from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import or_, select

from app.db import models as m
from app.db.enums import KgOtkStatus, KgState, PakDeviceKind, VerificationSessionStatus
from app.domain.production.exceptions import (
    PackingBatchArchivedError,
    PackingKgAlreadyPackedError,
    PackingKgScrappedError,
    PackingOtkInProgressError,
    PackingOtkNotPassedError,
)
from app.domain.production.schemas import PackingBlocker

if TYPE_CHECKING:
    from uuid import UUID

    from app.lib.exceptions import ApplicationConflictError

PACKING_ERRORS: dict[PackingBlocker, type[ApplicationConflictError]] = {
    PackingBlocker.ALREADY_PACKED: PackingKgAlreadyPackedError,
    PackingBlocker.SCRAPPED: PackingKgScrappedError,
    PackingBlocker.BATCH_ARCHIVED: PackingBatchArchivedError,
    PackingBlocker.OTK_IN_PROGRESS: PackingOtkInProgressError,
    PackingBlocker.OTK_NOT_PASSED: PackingOtkNotPassedError,
}
"""The error packing raises for each blocker; its code is the blocker's value."""


class PackingService(service.SQLAlchemyAsyncRepositoryService[m.KgUnit]):
    """Packing of KG units that passed OTK: the last production step, never undone.

    Packing locks the batch (shared) and then the KG unit, in the order
    verification sessions are opened, so a unit is never packed while an
    OTK-line PAK starts verifying it.
    """

    class Repo(repository.SQLAlchemyAsyncRepository[m.KgUnit]):
        """KG unit SQLAlchemy repository."""

        model_type = m.KgUnit
        id_attribute = "dev_eui"

    repository_type = Repo

    async def find_unit(self, code: str) -> tuple[m.KgUnit, PackingBlocker | None]:
        """Find a unit by its DevEUI or short ID, in any case, and tell whether it may be packed."""
        value = code.strip().lower()
        kg = await self.get_one_or_none(
            or_(
                m.KgUnit.dev_eui == value,
                m.KgUnit.short_id == value,
            ),
        )

        if kg is None:
            raise NotFoundError("KG unit not found.")

        return kg, await self._find_blocker(kg, kg.batch)

    async def pack(self, dev_eui: str, *, packed_by_id: UUID) -> m.KgUnit:
        unit = await self.repository.session.get(m.KgUnit, dev_eui)

        if unit is None:
            raise NotFoundError("KG unit not found.")

        # A shared lock keeps the batch from being archived before the packing commits.
        batch: m.Batch | None = await self.repository.session.scalar(
            select(m.Batch)
            .where(m.Batch.id == unit.batch_id)
            .with_for_update(read=True, of=m.Batch)
            .execution_options(populate_existing=True)
        )
        # Conflicts with the key-share lock a PAK takes to open a session.
        kg: m.KgUnit | None = await self.repository.session.scalar(
            select(m.KgUnit)
            .where(m.KgUnit.dev_eui == dev_eui)
            .with_for_update(of=m.KgUnit)
            .execution_options(populate_existing=True)
        )

        if batch is None or kg is None:
            raise NotFoundError("KG unit not found.")

        blocker = await self._find_blocker(kg, batch)

        if blocker is not None:
            raise PACKING_ERRORS[blocker]

        kg.state = KgState.PACKED
        kg.packed_at = datetime.now(UTC)
        kg.packed_by_id = packed_by_id
        await self.repository.session.flush()
        await self.repository.session.refresh(kg, attribute_names=("packed_by",))

        return kg

    async def _find_blocker(self, kg: m.KgUnit, batch: m.Batch) -> PackingBlocker | None:
        if kg.state is KgState.PACKED:
            return PackingBlocker.ALREADY_PACKED

        if kg.state is KgState.SCRAPPED:
            return PackingBlocker.SCRAPPED

        if batch.archived_at is not None:
            return PackingBlocker.BATCH_ARCHIVED

        if await self._is_on_otk_line(kg.dev_eui):
            return PackingBlocker.OTK_IN_PROGRESS

        if kg.otk_status is not KgOtkStatus.PASSED:
            return PackingBlocker.OTK_NOT_PASSED

        return None

    async def _is_on_otk_line(self, dev_eui: str) -> bool:
        running = await self.repository.session.scalar(
            select(m.VerificationSession.id).where(
                m.VerificationSession.dev_eui == dev_eui,
                m.VerificationSession.status == VerificationSessionStatus.RUNNING,
                m.VerificationSession.pak_kind == PakDeviceKind.OTK_LINE,
            )
        )

        return running is not None
