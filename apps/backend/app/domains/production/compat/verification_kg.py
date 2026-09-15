"""Production-side implementation of the narrow verification KG contract."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.quality.verification.contracts import VerificationKg, VerificationKgPort

from ..kg.repository import KgRepository


class ProductionVerificationKgAdapter(VerificationKgPort):
    def __init__(self, session: AsyncSession) -> None:
        self._repository = KgRepository(session)

    async def resolve_and_lock(
        self, *, dev_eui: str, related_dev_euis: list[str]
    ) -> VerificationKg | None:
        # KgRepository preserves the legacy deterministic DevEUI row order.
        units = await self._repository.get_many_by_dev_euis(
            [dev_eui, *related_dev_euis], for_update=True
        )
        for unit in units:
            if unit.dev_eui == dev_eui:
                return VerificationKg(dev_eui=unit.dev_eui, state=unit.state.value)
        return None
