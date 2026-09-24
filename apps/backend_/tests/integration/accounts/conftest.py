"""Account domain integration test fixtures.

These fixtures provide service instances for account-related tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

import pytest

from app.db.enums import UserRole
from app.domain.accounts.schemas import UserCreate
from app.domain.accounts.services import UserService
from app.lib.kratos import KratosClient
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import models as m


pytestmark = pytest.mark.anyio


class UserData(Protocol):
    def __call__(self, *, role: UserRole = ..., is_active: bool = ...) -> UserCreate: ...


class CreateUser(Protocol):
    async def __call__(self, *, role: UserRole = ..., is_active: bool = ...) -> m.User: ...


@pytest.fixture
async def user_service(session: AsyncSession) -> AsyncGenerator[UserService]:
    """Create UserService instance with the test session."""
    async with UserService.new(session) as service:
        yield service


@pytest.fixture
def user_data() -> UserData:
    """Return a builder of valid user input with a unique login."""

    def _build(*, role: UserRole = UserRole.OPERATOR, is_active: bool = True) -> UserCreate:
        # Kratos identities outlive per-test database cleanup, so logins must be unique.
        suffix = uuid4().hex[:8]
        return UserCreate(
            login=f"user-{suffix}",
            name="Test User",
            password=f"Test_User_{suffix}!",
            role=role,
            is_active=is_active,
        )

    return _build


@pytest.fixture
def create_user(
    user_service: UserService,
    kratos_client: KratosClient,
    user_data: UserData,
) -> CreateUser:
    """Return a helper that commits a user in PostgreSQL and Kratos."""

    async def _create(*, role: UserRole = UserRole.OPERATOR, is_active: bool = True) -> m.User:
        async with unit_of_work(user_service.repository.session) as uow:
            return await user_service.create_user(
                user_data(role=role, is_active=is_active), kratos=kratos_client, uow=uow
            )

    return _create
