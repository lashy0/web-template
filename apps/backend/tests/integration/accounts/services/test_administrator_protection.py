"""Administrators cannot lock themselves or everyone else out."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.db.enums import UserRole
from app.domain.accounts.exceptions import LastAdministratorError, SelfActionForbiddenError
from app.domain.accounts.services import UserService
from app.lib.kratos import KratosClient
from app.lib.uow import UnitOfWork, unit_of_work

if TYPE_CHECKING:
    from tests.integration.accounts.conftest import CreateUser

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
    pytest.mark.security,
]


async def test_last_administrator_cannot_be_demoted(
    user_service: UserService,
    create_user: CreateUser,
) -> None:
    administrator = await create_user(role=UserRole.ADMINISTRATOR)

    with pytest.raises(LastAdministratorError):
        await user_service.assign_role(administrator.id, UserRole.MANAGER)


async def test_last_administrator_cannot_be_deactivated(
    user_service: UserService,
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    administrator = await create_user(role=UserRole.ADMINISTRATOR)
    uow = UnitOfWork(user_service.repository.session)

    with pytest.raises(LastAdministratorError):
        await user_service.set_active(
            administrator.id,
            is_active=False,
            kratos=kratos_client,
            uow=uow,
        )


async def test_last_administrator_cannot_be_archived(
    user_service: UserService,
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    administrator = await create_user(role=UserRole.ADMINISTRATOR)
    uow = UnitOfWork(user_service.repository.session)

    with pytest.raises(LastAdministratorError):
        await user_service.set_archived(
            administrator.id,
            archived=True,
            kratos=kratos_client,
            uow=uow,
        )


async def test_last_administrator_cannot_be_deleted(
    user_service: UserService,
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    administrator = await create_user(role=UserRole.ADMINISTRATOR)
    uow = UnitOfWork(user_service.repository.session)

    with pytest.raises(LastAdministratorError):
        await user_service.delete_user(
            administrator.id,
            kratos=kratos_client,
            uow=uow,
        )


async def test_administrator_can_be_archived_when_another_remains(
    user_service: UserService,
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    administrator = await create_user(role=UserRole.ADMINISTRATOR)
    await create_user(role=UserRole.ADMINISTRATOR)

    async with unit_of_work(user_service.repository.session) as uow:
        archived = await user_service.set_archived(
            administrator.id,
            archived=True,
            kratos=kratos_client,
            uow=uow,
        )

    assert archived.archived_at is not None


async def test_administrator_cannot_demote_themselves(
    user_service: UserService,
    create_user: CreateUser,
) -> None:
    actor = await create_user(role=UserRole.ADMINISTRATOR)
    await create_user(role=UserRole.ADMINISTRATOR)

    with pytest.raises(SelfActionForbiddenError):
        await user_service.assign_role(actor.id, UserRole.MANAGER, actor_id=actor.id)


async def test_administrator_cannot_deactivate_themselves(
    user_service: UserService,
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    actor = await create_user(role=UserRole.ADMINISTRATOR)
    await create_user(role=UserRole.ADMINISTRATOR)
    uow = UnitOfWork(user_service.repository.session)

    with pytest.raises(SelfActionForbiddenError):
        await user_service.set_active(
            actor.id,
            is_active=False,
            kratos=kratos_client,
            uow=uow,
            actor_id=actor.id,
        )


async def test_administrator_cannot_archive_themselves(
    user_service: UserService,
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    actor = await create_user(role=UserRole.ADMINISTRATOR)
    await create_user(role=UserRole.ADMINISTRATOR)
    uow = UnitOfWork(user_service.repository.session)

    with pytest.raises(SelfActionForbiddenError):
        await user_service.set_archived(
            actor.id,
            archived=True,
            kratos=kratos_client,
            uow=uow,
            actor_id=actor.id,
        )


async def test_administrator_cannot_delete_themselves(
    user_service: UserService,
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    actor = await create_user(role=UserRole.ADMINISTRATOR)
    await create_user(role=UserRole.ADMINISTRATOR)
    uow = UnitOfWork(user_service.repository.session)

    with pytest.raises(SelfActionForbiddenError):
        await user_service.delete_user(
            actor.id,
            kratos=kratos_client,
            uow=uow,
            actor_id=actor.id,
        )


async def test_administrator_can_demote_another_administrator(
    user_service: UserService,
    create_user: CreateUser,
) -> None:
    actor = await create_user(role=UserRole.ADMINISTRATOR)
    other = await create_user(role=UserRole.ADMINISTRATOR)

    demoted = await user_service.assign_role(other.id, UserRole.MANAGER, actor_id=actor.id)

    assert demoted.role == UserRole.MANAGER
