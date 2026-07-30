from typing import cast

import pytest
from pytest_mock import MockerFixture
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.unit.health.mocks import PostgresEngineMock, RedisClientMock


@pytest.fixture
def postgres_engine_mock(
    mocker: MockerFixture,
) -> PostgresEngineMock:
    raw_engine = mocker.MagicMock(spec=AsyncEngine)
    connection = mocker.AsyncMock()

    context_manager = mocker.MagicMock()

    context_manager.__aenter__ = mocker.AsyncMock(
        return_value=connection,
    )
    context_manager.__aexit__ = mocker.AsyncMock(
        return_value=False,
    )

    raw_engine.begin.return_value = context_manager

    return PostgresEngineMock(
        engine=cast(AsyncEngine, raw_engine),
        raw_engine=raw_engine,
        connection=connection,
    )


@pytest.fixture
def redis_client_mock(
    mocker: MockerFixture,
) -> RedisClientMock:
    raw_client = mocker.MagicMock(spec=Redis)
    raw_client.ping = mocker.AsyncMock(return_value=True)

    return RedisClientMock(
        client=cast(Redis, raw_client),
        raw_client=raw_client,
    )
