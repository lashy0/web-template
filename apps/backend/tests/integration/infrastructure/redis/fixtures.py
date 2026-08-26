from collections.abc import AsyncIterator

import pytest
from redis.asyncio import Redis

from app.core.config import Settings
from app.infrastructure.redis.client import create_redis_client


@pytest.fixture
async def redis_client(test_settings: Settings) -> AsyncIterator[Redis]:
    client = create_redis_client(test_settings)

    try:
        yield client
    finally:
        await client.aclose()
