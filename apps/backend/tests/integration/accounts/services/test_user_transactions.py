"""User changes stay consistent with Kratos across commits and rollbacks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import models as m
from app.domain.accounts.services import UserService
from app.lib.kratos import KratosClient
from app.lib.kratos.exceptions import KratosIdentityNotFoundError, KratosUnavailableError
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from app.domain.accounts.schemas import UserCreate
    from tests.integration.accounts.conftest import CreateUser, UserData

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


class _KratosDown:
    """Kratos whose identity updates fail after the request reached it."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def set_active(self, _identity_id: UUID, *, is_active: bool) -> None:
        self.calls.append(f"set_active:{is_active}")
        raise KratosUnavailableError(detail="Kratos request failed")

    async def revoke_all_sessions(self, _identity_id: UUID) -> None:
        self.calls.append("revoke_all_sessions")


async def _set_active(
    sessionmaker: async_sessionmaker[AsyncSession],
    user_id: UUID,
    kratos: object,
    *,
    is_active: bool,
) -> None:
    async with sessionmaker() as session, unit_of_work(session) as uow:
        await UserService(session=session).set_active(
            user_id,
            is_active=is_active,
            kratos=cast(Any, kratos),
            uow=uow,
        )


async def _stored(sessionmaker: async_sessionmaker[AsyncSession], user_id: UUID) -> m.User:
    async with sessionmaker() as session:
        user = await session.get(m.User, user_id)

    assert user is not None

    return user


async def _create_and_roll_back(
    sessionmaker: async_sessionmaker[AsyncSession],
    kratos: KratosClient,
    data: UserCreate,
) -> m.User:
    """Create a user in a transaction whose request then fails."""
    created: list[m.User] = []

    with pytest.raises(RuntimeError):
        async with sessionmaker() as session, unit_of_work(session) as uow:
            created.append(
                await UserService(session=session).create_user(
                    data,
                    kratos=kratos,
                    uow=uow,
                )
            )

            raise RuntimeError("request failed")

    return created[0]


async def test_rolled_back_creation_leaves_no_local_user(
    sessionmaker: async_sessionmaker[AsyncSession],
    kratos_client: KratosClient,
    user_service: UserService,
    user_data: UserData,
) -> None:
    user = await _create_and_roll_back(sessionmaker, kratos_client, user_data())

    assert await user_service.get_one_or_none(id=user.id) is None


async def test_rolled_back_creation_removes_identity(
    sessionmaker: async_sessionmaker[AsyncSession],
    kratos_client: KratosClient,
    user_data: UserData,
) -> None:
    user = await _create_and_roll_back(sessionmaker, kratos_client, user_data())

    with pytest.raises(KratosIdentityNotFoundError):
        await kratos_client.get_identity(user.identity_id)


async def test_rolled_back_creation_frees_login(
    sessionmaker: async_sessionmaker[AsyncSession],
    kratos_client: KratosClient,
    user_service: UserService,
    user_data: UserData,
) -> None:
    data = user_data()
    await _create_and_roll_back(sessionmaker, kratos_client, data)

    async with unit_of_work(user_service.repository.session) as uow:
        retried = await user_service.create_user(data, kratos=kratos_client, uow=uow)

    assert retried.identity_login == data.login


async def test_deactivation_commits_when_kratos_fails_after_commit(
    sessionmaker: async_sessionmaker[AsyncSession],
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    user = await create_user()
    kratos_down = _KratosDown()

    await _set_active(sessionmaker, user.id, kratos_down, is_active=False)

    assert (await _stored(sessionmaker, user.id)).identity_active is False
    assert kratos_down.calls == ["set_active:False", "revoke_all_sessions"]
    assert (await kratos_client.get_identity(user.identity_id)).is_active is True


async def test_repeated_deactivation_repairs_kratos(
    sessionmaker: async_sessionmaker[AsyncSession],
    kratos_client: KratosClient,
    create_user: CreateUser,
) -> None:
    user = await create_user()
    await _set_active(sessionmaker, user.id, _KratosDown(), is_active=False)

    await _set_active(sessionmaker, user.id, kratos_client, is_active=False)

    assert (await kratos_client.get_identity(user.identity_id)).is_active is False


async def test_activation_fails_before_commit_when_kratos_is_unavailable(
    sessionmaker: async_sessionmaker[AsyncSession],
    create_user: CreateUser,
) -> None:
    user = await create_user(is_active=False)

    with pytest.raises(KratosUnavailableError):
        await _set_active(sessionmaker, user.id, _KratosDown(), is_active=True)

    assert (await _stored(sessionmaker, user.id)).identity_active is False
