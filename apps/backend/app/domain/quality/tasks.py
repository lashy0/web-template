"""Background tasks of the quality domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.domain.quality.services import VerificationSessionService
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from app.lib.worker import WorkerContext

logger = structlog.get_logger()

EXPIRE_BATCH_SIZE = 100
"""Sessions closed per transaction, so one run never holds many row locks."""


async def expire_stale_verification_sessions(ctx: WorkerContext) -> int:
    """Close running verification sessions the PAK stopped reporting, as incomplete.

    Runs every minute; a session is stale after ``BACKEND_VERIFICATION_SESSION_TTL_MINUTES``
    without a report. Returns the number of sessions closed.
    """
    idle_for = ctx["settings"].verification.session_ttl
    total = 0

    while True:
        async with (
            ctx["alchemy"].get_session() as db_session,
            unit_of_work(db_session),
            VerificationSessionService.new(session=db_session) as sessions,
        ):
            expired = await sessions.expire_stale(idle_for=idle_for, limit=EXPIRE_BATCH_SIZE)

        total += expired

        if expired < EXPIRE_BATCH_SIZE:
            break

    if total:
        logger.info("verification.sessions_expired", count=total)

    return total


__all__ = ("expire_stale_verification_sessions",)
