from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, literal, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.kg.models import KgState
from app.modules.kg.repositories import KgRepository
from app.modules.kg.repositories import unit as unit_repository
from app.modules.kg.schemas.state import KgCurrentState
from app.modules.verification.models import VerificationSessionStatus


@pytest.mark.unit
@pytest.mark.parametrize(
    ("session_status", "expected_current_state"),
    [
        pytest.param(
            VerificationSessionStatus.FAILED,
            KgCurrentState.OTK_FAILED,
            id="failed",
        ),
        pytest.param(
            VerificationSessionStatus.ABORTED,
            KgCurrentState.OTK_ABORTED,
            id="aborted",
        ),
        pytest.param(
            VerificationSessionStatus.INCOMPLETE,
            KgCurrentState.OTK_INCOMPLETE,
            id="incomplete",
        ),
    ],
)
def test_current_state_keeps_terminal_verification_outcomes_distinct(
    monkeypatch: pytest.MonkeyPatch,
    session_status: VerificationSessionStatus,
    expected_current_state: KgCurrentState,
) -> None:
    monkeypatch.setattr(
        unit_repository,
        "KgUnit",
        SimpleNamespace(state=literal(KgState.REGISTERED.value)),
    )
    latest_session = select(literal(session_status.value).label("status")).subquery()
    expression = KgRepository._current_state_expression(latest_session)

    with create_engine("sqlite://").connect() as connection:
        current_state = connection.scalar(select(expression))

    assert current_state == expected_current_state.value


@pytest.mark.unit
async def test_has_scrapped_by_batch_checks_only_scrapped_units() -> None:
    session = SimpleNamespace(scalar=AsyncMock(return_value=True))

    assert await KgRepository(cast(AsyncSession, session)).has_scrapped_by_batch(uuid4())

    statement = session.scalar.await_args.args[0]
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "kg_units.state = 'SCRAPPED'" in sql


@pytest.mark.unit
async def test_list_batch_items_returns_latest_session_data_in_one_query() -> None:
    batch_id = uuid4()
    result = SimpleNamespace(
        tuples=lambda: [
            (
                "a1b2c3d4e5f60708",
                KgCurrentState.OTK_PASSED,
                "1.4.2",
                None,
                2,
            ),
            (
                "a1b2c3d4e5f60709",
                KgCurrentState.REGISTERED,
                None,
                None,
                2,
            ),
        ]
    )
    session = SimpleNamespace(execute=AsyncMock(return_value=result))

    items, total = await KgRepository(session).list_batch_items(
        batch_id,
        page=1,
        page_size=25,
        q=None,
        current_state=None,
    )

    assert [item.dev_eui for item in items] == ["a1b2c3d4e5f60708", "a1b2c3d4e5f60709"]
    assert items[0].firmware_version == "1.4.2"
    assert items[0].current_state is KgCurrentState.OTK_PASSED
    assert items[1].current_state is KgCurrentState.REGISTERED
    assert items[1].firmware_version is None
    assert items[1].last_verification_at is None
    assert total == 2
    session.execute.assert_awaited_once()
