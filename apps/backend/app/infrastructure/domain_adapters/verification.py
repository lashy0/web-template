"""SQLAlchemy adapters connecting quality verification to its consumers.

This is the sole place where verification persistence is joined with another
domain's ORM model. Domain modules depend on their consumer-owned ports only.
"""

from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Subquery

from app.domains.equipment.pak.contracts import PakVerificationHistoryPort
from app.domains.equipment.pak.model import PakDevice
from app.domains.production.contracts import (
    LatestVerificationProjectionPort,
    VerificationHistoryPort,
)
from app.domains.production.kg.model import KgUnit
from app.domains.production.kg.repository import KgRepository
from app.domains.quality.verification.contracts import (
    VerificationKg,
    VerificationKgPort,
    VerificationPakPort,
)
from app.domains.quality.verification.model import VerificationSession
from app.domains.quality.verification.repository import VerificationRepository


class SqlAlchemyVerificationHistoryProvider(VerificationHistoryPort, PakVerificationHistoryPort):
    """Answer deletion-history ports using the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._verification = VerificationRepository(session)

    async def has_history_for_batch(self, batch_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        VerificationSession.kg_dev_eui == KgUnit.dev_eui,
                        KgUnit.batch_id == batch_id,
                    )
                )
            )
        )

    async def has_history_for_kg(self, dev_eui: str) -> bool:
        return await self._verification.has_history_for_kg(dev_eui)

    async def has_history_for_pak(self, pak_id: UUID) -> bool:
        return await self._verification.has_history_for_pak(pak_id)


class SqlAlchemyLatestVerificationProjection(LatestVerificationProjectionPort):
    """Expose quality's latest-session relation through production's read port."""

    def latest_verification_projection(self) -> Subquery:
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


class ProductionVerificationKgAdapter(VerificationKgPort):
    """Expose only the KG facts consumed by quality's verification workflow."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = KgRepository(session)

    async def resolve_and_lock(
        self, *, dev_eui: str, related_dev_euis: list[str]
    ) -> VerificationKg | None:
        # KgRepository preserves the deterministic DevEUI row order that makes
        # this multi-row lock deadlock-free.
        units = await self._repository.get_many_by_dev_euis(
            [dev_eui, *related_dev_euis], for_update=True
        )
        for unit in units:
            if unit.dev_eui == dev_eui:
                return VerificationKg(dev_eui=unit.dev_eui, state=unit.state.value)
        return None


class EquipmentVerificationPakAdapter(VerificationPakPort):
    """Expose only verification's PAK identity facts."""

    def __init__(self, pak: PakDevice) -> None:
        self._pak = pak

    @property
    def id(self) -> UUID:
        return self._pak.id

    @property
    def code(self) -> str:
        return self._pak.code

    @property
    def oauth_client_id(self) -> str:
        return self._pak.oauth_client_id


def adapt_pak(pak: PakDevice) -> VerificationPakPort:
    return EquipmentVerificationPakAdapter(pak)
