from typing import cast

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.health.types import PostgresEngineMock


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
