"""Production consumer adapter for quality-owned verification facts.

This module deliberately contains no verification ORM or SQL.  The quality
provider owns that persistence; production retains only its current-state
mapping and consumes its bulk projection.
"""

from typing import Any

from sqlalchemy import case, literal
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from app.contexts.production.kg.schemas.state import KgCurrentState
from app.contexts.quality.verification.adapters import (
    VerificationHistoryProvider,
    latest_verification_projection,
)

QualityVerificationHistoryAdapter = VerificationHistoryProvider

__all__ = [
    "QualityVerificationHistoryAdapter",
    "current_kg_state_expression",
    "latest_verification_projection",
]


def current_kg_state_expression(persistent_state: Any, latest: Subquery) -> ColumnElement[str]:
    """Preserve legacy precedence: SCRAPPED > latest verification > REGISTERED."""
    return case(
        (persistent_state == "SCRAPPED", literal(KgCurrentState.SCRAPPED.value)),
        (
            latest.c.status == "RUNNING",
            literal(KgCurrentState.ON_OTK.value),
        ),
        (
            latest.c.status == "PASSED",
            literal(KgCurrentState.OTK_PASSED.value),
        ),
        (
            latest.c.status == "FAILED",
            literal(KgCurrentState.OTK_FAILED.value),
        ),
        (
            latest.c.status == "ABORTED",
            literal(KgCurrentState.OTK_ABORTED.value),
        ),
        (
            latest.c.status == "INCOMPLETE",
            literal(KgCurrentState.OTK_INCOMPLETE.value),
        ),
        else_=literal(KgCurrentState.REGISTERED.value),
    )
