from dataclasses import dataclass

from pytest_mock import AsyncMockType, MockType
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(slots=True)
class PostgresEngineMock:
    engine: AsyncEngine
    raw_engine: MockType
    connection: AsyncMockType
