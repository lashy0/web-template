"""KG read-model expressions owned by production."""

from typing import Any

from sqlalchemy import case, literal
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from .schemas.state import KgCurrentState


def current_kg_state_expression(persistent_state: Any, latest: Subquery) -> ColumnElement[str]:
    """Precedence of the KG current state: SCRAPPED > latest verification > REGISTERED."""
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
