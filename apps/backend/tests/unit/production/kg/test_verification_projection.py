from types import SimpleNamespace

import pytest
from sqlalchemy import literal

from app.contexts.production.compat.verification import current_kg_state_expression
from app.contexts.production.kg.schemas.state import KgCurrentState


@pytest.mark.unit
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("RUNNING", KgCurrentState.ON_OTK),
        ("PASSED", KgCurrentState.OTK_PASSED),
        ("FAILED", KgCurrentState.OTK_FAILED),
        ("ABORTED", KgCurrentState.OTK_ABORTED),
        ("INCOMPLETE", KgCurrentState.OTK_INCOMPLETE),
    ],
)
def test_current_state_maps_each_latest_verification_status(
    status: str, expected: KgCurrentState
) -> None:
    latest = SimpleNamespace(c=SimpleNamespace(status=literal(status)))
    expression = current_kg_state_expression(literal("REGISTERED"), latest)
    assert expected.value in str(expression.compile(compile_kwargs={"literal_binds": True}))


@pytest.mark.unit
def test_scrapped_precedes_latest_verification_status() -> None:
    latest = SimpleNamespace(c=SimpleNamespace(status=literal("PASSED")))
    expression = current_kg_state_expression(literal("SCRAPPED"), latest)
    compiled = str(expression.compile(compile_kwargs={"literal_binds": True}))
    assert compiled.index("SCRAPPED") < compiled.index("PASSED")
