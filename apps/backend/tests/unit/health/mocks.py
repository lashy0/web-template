from dataclasses import dataclass

from pytest_mock import AsyncMockType, MockType
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(slots=True)
class PostgresEngineMock:
    engine: AsyncEngine
    raw_engine: MockType
    connection: AsyncMockType


@dataclass(slots=True)
class RedisClientMock:
    client: Redis
    raw_client: MockType
