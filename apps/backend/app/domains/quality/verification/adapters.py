"""Provider adapter exposed to production without leaking verification ORM there."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Subquery

from .model import VerificationSession
from .repository import VerificationRepository


class VerificationHistoryProvider:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = VerificationRepository(session)

    async def has_history_for_batch(self, batch_id: UUID) -> bool:
        return await self._repository.has_history_for_batch(batch_id)

    async def has_history_for_kg(self, dev_eui: str) -> bool:
        return await self._repository.has_history_for_kg(dev_eui)

    async def has_history_for_pak(self, pak_id: UUID) -> bool:
        return await self._repository.has_history_for_pak(pak_id)


class QualityPakVerificationHistoryAdapter(VerificationHistoryProvider):
    """Quality-owned provider for equipment's narrow deletion-history contract."""


def latest_verification_projection() -> Subquery:
    """One bulk latest-verification relation, consumed by KG projections."""
    return select(
        VerificationSession.id.label("id"),
        VerificationSession.kg_dev_eui.label("kg_dev_eui"),
        VerificationSession.status.label("status"),
        VerificationSession.firmware_version.label("firmware_version"),
        VerificationSession.started_at.label("started_at"),
        func.row_number()
        .over(
            partition_by=VerificationSession.kg_dev_eui,
            order_by=(VerificationSession.started_at.desc(), VerificationSession.id.desc()),
        )
        .label("rank"),
    ).subquery()
