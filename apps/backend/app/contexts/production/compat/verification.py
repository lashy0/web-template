"""Temporary adapter from production contracts to legacy verification persistence."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.verification.repositories.session import VerificationSessionRepository


class LegacyVerificationHistoryAdapter:
    """Compatibility adapter replaceable when quality/verification is extracted."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = VerificationSessionRepository(session)

    async def has_history_for_batch(self, batch_id: UUID) -> bool:
        return bool(await self._repository.exists_by_batch_id(batch_id))
