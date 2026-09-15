from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repository import VerificationRepository
from ..transaction import verification_transaction
from .complete import close_incomplete


class ReconcileStaleVerificationSessions:
    """One caller-owned stale-row claim batch; PostgreSQL SKIP LOCKED is required."""

    def __init__(self, repository: VerificationRepository, *, session_ttl: timedelta) -> None:
        self._repository = repository
        self._session_ttl = session_ttl

    async def execute(self, *, batch_size: int) -> int:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        now = datetime.now(UTC)
        claimed = await self._repository.claim_stale_running(
            cutoff=now - self._session_ttl, limit=batch_size
        )
        for item in claimed:
            await close_incomplete(self._repository, item, completed_at=now)
        return len(claimed)


async def reconcile_stale_sessions(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_ttl: timedelta,
    batch_size: int = 100,
) -> int:
    """Application runner: each claimed batch gets a short independent transaction."""
    total = 0
    while True:
        async with verification_transaction(session_factory) as session:
            claimed = await ReconcileStaleVerificationSessions(
                VerificationRepository(session), session_ttl=session_ttl
            ).execute(batch_size=batch_size)
        total += claimed
        if claimed < batch_size:
            return total
