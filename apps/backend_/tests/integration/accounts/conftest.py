"""Account domain integration test fixtures.

These fixtures provide service instances for account-related tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.domain.accounts.services import UserService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.anyio


@pytest.fixture
async def user_service(session: AsyncSession) -> AsyncGenerator[UserService]:
    """Create UserService instance with the test session."""
    async with UserService.new(session) as service:
        yield service
