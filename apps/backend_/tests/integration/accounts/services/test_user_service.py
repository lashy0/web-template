"""User service integration tests against PostgreSQL and Kratos."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.domain.accounts.schemas import UserUpdate
from app.domain.accounts.services import UserService
from app.lib.kratos import KratosClient
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from tests.integration.accounts.conftest import CreateUser

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


async def test_create_user_creates_kratos_identity(
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    user = await create_user()

    identity = await kratos_client.get_identity(user.identity_id)
    assert identity.login == user.identity_login
    assert identity.is_active is True


async def test_update_user_renames_kratos_identity(
    user_service: UserService,
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    user = await create_user()
    login = f"{user.identity_login}-renamed"

    async with unit_of_work(user_service.repository.session) as uow:
        updated = await user_service.update_user(
            user.id,
            UserUpdate(login=login),
            kratos=kratos_client,
            uow=uow,
        )

    assert updated.identity_login == login
    assert (await kratos_client.get_identity(user.identity_id)).login == login


async def test_activate_user_activates_kratos_identity(
    user_service: UserService,
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    user = await create_user(is_active=False)

    async with unit_of_work(user_service.repository.session) as uow:
        activated = await user_service.set_active(
            user.id,
            is_active=True,
            kratos=kratos_client,
            uow=uow,
        )

    assert activated.identity_active is True
    assert (await kratos_client.get_identity(user.identity_id)).is_active is True


async def test_archive_user_deactivates_kratos_identity(
    user_service: UserService,
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    user = await create_user()

    async with unit_of_work(user_service.repository.session) as uow:
        archived = await user_service.set_archived(
            user.id,
            archived=True,
            kratos=kratos_client,
            uow=uow,
        )

    assert archived.archived_at is not None
    assert archived.identity_active is False
    assert (await kratos_client.get_identity(user.identity_id)).is_active is False
