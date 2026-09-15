"""Inbound adapters: production implementing ports owned by other modules.

The composition root installs these, so no other module constructs production
persistence itself.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.quality.verification.contracts import VerificationKg, VerificationKgPort

from .kg.repository import KgRepository


class ProductionVerificationKgAdapter(VerificationKgPort):
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
