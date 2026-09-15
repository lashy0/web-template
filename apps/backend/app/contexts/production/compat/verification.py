"""Temporary adapter from production contracts to legacy verification persistence.

This is the only production boundary allowed to know the legacy verification
ORM until quality/verification is extracted.  The projection is intentionally
bulk SQL, so KG list endpoints keep their single-query behaviour.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import case, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from app.contexts.production.kg.schemas.state import KgCurrentState
from app.modules.verification.models import VerificationSession, VerificationSessionStatus
from app.modules.verification.repositories.session import VerificationSessionRepository


class LegacyVerificationHistoryAdapter:
    """Compatibility adapter replaceable when quality/verification is extracted."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = VerificationSessionRepository(session)

    async def has_history_for_batch(self, batch_id: UUID) -> bool:
        return bool(await self._repository.exists_by_batch_id(batch_id))

    async def has_history_for_kg(self, dev_eui: str) -> bool:
        return bool(await self._repository.exists_by_kg_dev_eui(dev_eui))


def latest_verification_projection() -> Subquery:
    """Latest verification fact per KG, including list-detail fields."""
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


def current_kg_state_expression(persistent_state: Any, latest: Subquery) -> ColumnElement[str]:
    """Preserve legacy precedence: SCRAPPED > latest verification > REGISTERED."""
    return case(
        (persistent_state == "SCRAPPED", literal(KgCurrentState.SCRAPPED.value)),
        (
            latest.c.status == VerificationSessionStatus.RUNNING,
            literal(KgCurrentState.ON_OTK.value),
        ),
        (
            latest.c.status == VerificationSessionStatus.PASSED,
            literal(KgCurrentState.OTK_PASSED.value),
        ),
        (
            latest.c.status == VerificationSessionStatus.FAILED,
            literal(KgCurrentState.OTK_FAILED.value),
        ),
        (
            latest.c.status == VerificationSessionStatus.ABORTED,
            literal(KgCurrentState.OTK_ABORTED.value),
        ),
        (
            latest.c.status == VerificationSessionStatus.INCOMPLETE,
            literal(KgCurrentState.OTK_INCOMPLETE.value),
        ),
        else_=literal(KgCurrentState.REGISTERED.value),
    )
