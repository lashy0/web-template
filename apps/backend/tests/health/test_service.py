import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.modules.health.service import is_postgres_ready
from tests.health.types import PostgresEngineMock


@pytest.mark.unit
async def test_is_postgres_ready(
    postgres_engine_mock: PostgresEngineMock,
) -> None:
    result = await is_postgres_ready(
        postgres_engine_mock.engine,
    )

    assert result is True

    postgres_engine_mock.raw_engine.begin.assert_called_once_with()
    postgres_engine_mock.connection.execute.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.parametrize(
    "exception",
    [
        pytest.param(
            SQLAlchemyError("Postgres is unavailable"),
            id="sqlalchemy-error",
        ),
        pytest.param(
            TimeoutError(),
            id="timeout-error",
        ),
    ],
)
async def test_is_postgres_not_ready_on_expected_error(
    postgres_engine_mock: PostgresEngineMock,
    exception: Exception,
) -> None:
    postgres_engine_mock.connection.execute.side_effect = exception

    result = await is_postgres_ready(
        postgres_engine_mock.engine,
    )

    assert result is False

    postgres_engine_mock.raw_engine.begin.assert_called_once_with()
    postgres_engine_mock.connection.execute.assert_awaited_once()
