"""User service integration tests against PostgreSQL and Kratos."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import models as m
from app.db.enums import UserRole
from app.domain.accounts.schemas import UserCreate, UserUpdate
from app.domain.accounts.services import UserService
from app.lib.kratos import KratosClient

pytestmark = [pytest.mark.anyio, pytest.mark.integration, pytest.mark.services]


async def test_seeded_users_exist_in_postgresql_and_kratos(
    sessionmaker: async_sessionmaker[AsyncSession],
    kratos_client: KratosClient,
    seeded_db: None,
) -> None:
    """Seed data is created through UserService in both backing systems."""
    async with sessionmaker() as session:
        users = list((await session.scalars(select(m.User))).all())

    assert {user.identity_login for user in users} == {
        "administrator",
        "operator",
        "archived-user",
    }

    for user in users:
        identity = await kratos_client.get_identity(user.identity_id)
        assert identity.login == user.identity_login
        assert identity.is_active is user.identity_active


async def test_user_lifecycle_is_consistent_in_postgresql_and_kratos(
    user_service: UserService,
    kratos_client: KratosClient,
    db_cleanup: None,
) -> None:
    """Create, rename and archive a user across both systems."""
    user = await user_service.create_user(
        UserCreate(
            login="kratos-integration-user",
            name="Kratos Integration User",
            password="KratosIntegration_2026!",
            role=UserRole.OPERATOR,
        ),
        kratos=kratos_client,
    )

    identity = await kratos_client.get_identity(user.identity_id)

    assert identity.login == user.identity_login == "kratos-integration-user"
    assert identity.is_active is user.identity_active is True

    updated_user = await user_service.update_user(
        user.id,
        UserUpdate(login="kratos-integration-renamed"),
        kratos=kratos_client,
    )
    updated_identity = await kratos_client.get_identity(user.identity_id)

    assert updated_user.identity_login == updated_identity.login == "kratos-integration-renamed"

    archived_user = await user_service.set_archived(
        user.id,
        archived=True,
        kratos=kratos_client,
    )
    archived_identity = await kratos_client.get_identity(user.identity_id)

    assert archived_user.archived_at is not None
    assert archived_identity.is_active is archived_user.identity_active is False
