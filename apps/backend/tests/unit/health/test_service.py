import pytest
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.modules.health.service import is_postgres_ready, is_redis_ready
from tests.unit.health.mocks import PostgresEngineMock, RedisClientMock

READINESS_TIMEOUT = 2.0


@pytest.mark.unit
async def test_is_postgres_ready(
    postgres_engine_mock: PostgresEngineMock,
) -> None:
    result = await is_postgres_ready(
        postgres_engine_mock.engine,
        timeout=READINESS_TIMEOUT,
    )

    assert result is True

    postgres_engine_mock.raw_engine.begin.assert_called_once_with()
    postgres_engine_mock.connection.execute.assert_awaited_once()


@pytest.mark.unit
async def test_is_redis_ready(
    redis_client_mock: RedisClientMock,
) -> None:
    result = await is_redis_ready(
        redis_client_mock.client,
        timeout=READINESS_TIMEOUT,
    )

    assert result is True

    redis_client_mock.raw_client.ping.assert_awaited_once_with()


@pytest.mark.unit
@pytest.mark.parametrize(
    "exception",
    [
        pytest.param(
            RedisError("Redis is unavailable"),
            id="redis-error",
        ),
        pytest.param(
            TimeoutError(),
            id="timeout-error",
        ),
    ],
)
async def test_is_redis_not_ready_on_expected_error(
    redis_client_mock: RedisClientMock,
    exception: Exception,
) -> None:
    redis_client_mock.raw_client.ping.side_effect = exception

    result = await is_redis_ready(
        redis_client_mock.client,
        timeout=READINESS_TIMEOUT,
    )

    assert result is False

    redis_client_mock.raw_client.ping.assert_awaited_once_with()


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
        timeout=READINESS_TIMEOUT,
    )

    assert result is False

    postgres_engine_mock.raw_engine.begin.assert_called_once_with()
    postgres_engine_mock.connection.execute.assert_awaited_once()
