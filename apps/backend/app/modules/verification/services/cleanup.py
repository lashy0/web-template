from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.kg.services import KgService

from ..repositories import (
    VerificationSessionRepository,
    VerificationStepRepository,
)
from .session import VerificationSessionService
from .transactions import transaction


class VerificationCleanupService:
    """Expire batches in separate transactions; skip rows owned by active requests."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        session_ttl: timedelta,
    ) -> None:
        self._session_factory = session_factory
        self._session_ttl = session_ttl

    async def expire_stale_sessions(
        self,
        *,
        batch_size: int = 100,
    ) -> int:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        total_expired = 0

        while True:
            now = datetime.now(UTC)
            cutoff = now - self._session_ttl

            async with transaction(self._session_factory) as session:
                verification_repository = VerificationSessionRepository(session)
                step_repository = VerificationStepRepository(session)
                kg_service = KgService(session)

                stale_sessions = await verification_repository.list_stale_running_for_update(
                    cutoff=cutoff,
                    limit=batch_size,
                )

                if not stale_sessions:
                    return total_expired

                await kg_service.lock_for_update([item.kg_dev_eui for item in stale_sessions])

                for verification_session in stale_sessions:
                    await VerificationSessionService(session).close_incomplete(
                        verification_repository,
                        step_repository,
                        kg_service,
                        verification_session,
                        completed_at=now,
                    )

                expired_count = len(stale_sessions)
                total_expired += expired_count

            if expired_count < batch_size:
                return total_expired
