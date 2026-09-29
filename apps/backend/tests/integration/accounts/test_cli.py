"""``app users`` commands against the test PostgreSQL and Kratos."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import pytest
from click.testing import CliRunner, Result
from sqlalchemy import select

from app.db import models as m
from app.db.enums import UserRole
from app.domain.accounts.cli import ADMIN_LOGIN, CLI_ACTOR, users_group
from app.lib.validation import validate_password

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.lib.kratos import KratosClient
    from tests.integration.accounts.conftest import UserData

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


async def _invoke(arguments: list[str], password: str | None = None) -> Result:
    prompts = f"{password}\n{password}\n" if password is not None else None
    # The command runs its own event loop, so it cannot run on the test's loop.
    return await anyio.to_thread.run_sync(lambda: CliRunner().invoke(users_group, arguments, input=prompts))


async def _create(user_data: UserData, role: str) -> str:
    data = user_data()
    result = await _invoke(["create", "--login", data.login, "--name", data.name, "--role", role], data.password)
    assert result.exit_code == 0, result.output
    return data.login


async def test_create_command_creates_user_in_kratos_and_database(
    session: AsyncSession,
    kratos_client: KratosClient,
    user_data: UserData,
) -> None:
    data = user_data()

    result = await _invoke(
        ["create", "--login", data.login, "--name", data.name, "--role", "administrator"],
        data.password,
    )

    assert result.exit_code == 0, result.output
    user = await session.scalar(select(m.User).where(m.User.identity_login == data.login))
    assert user is not None
    assert user.role == UserRole.ADMINISTRATOR
    assert (await kratos_client.get_identity(user.identity_id)).login == data.login
    entry = await session.scalar(select(m.AuditLog).where(m.AuditLog.target_id == str(user.id)))
    assert entry is not None
    assert (entry.action, entry.actor_login) == ("user.created", CLI_ACTOR)


async def test_create_command_rejects_invalid_password(
    session: AsyncSession,
    kratos_client: KratosClient,
    user_data: UserData,
) -> None:
    data = user_data()

    result = await _invoke(
        ["create", "--login", data.login, "--name", data.name, "--role", "operator"],
        "short",
    )

    assert result.exit_code == 1
    assert await session.scalar(select(m.User).where(m.User.identity_login == data.login)) is None


async def test_ensure_admin_creates_administrator_with_generated_password(
    session: AsyncSession,
    kratos_client: KratosClient,
) -> None:
    result = await _invoke(["ensure-admin"])

    assert result.exit_code == 0, result.output
    user = await session.scalar(select(m.User).where(m.User.identity_login == ADMIN_LOGIN))
    assert user is not None
    try:
        assert user.role == UserRole.ADMINISTRATOR
        password = result.output.splitlines()[0].rsplit(" ", 1)[1]
        assert validate_password(password) == password
    finally:
        # The login is fixed, so the identity must not outlive the test.
        await kratos_client.delete_identity(user.identity_id)


async def test_ensure_admin_does_nothing_while_an_active_administrator_exists(
    session: AsyncSession,
    user_data: UserData,
) -> None:
    await _create(user_data, "administrator")

    result = await _invoke(["ensure-admin"])

    assert result.exit_code == 0, result.output
    assert result.output == ""
    assert await session.scalar(select(m.User).where(m.User.identity_login == ADMIN_LOGIN)) is None


async def test_reset_password_sets_generated_password(
    session: AsyncSession,
    user_data: UserData,
) -> None:
    login = await _create(user_data, "operator")

    result = await _invoke(["reset-password", login.upper()])

    assert result.exit_code == 0, result.output
    password = result.output.rsplit(" ", 1)[1].strip()
    assert validate_password(password) == password
    user = await session.scalar(select(m.User).where(m.User.identity_login == login))
    assert user is not None
    entry = await session.scalar(
        select(m.AuditLog).where(m.AuditLog.target_id == str(user.id), m.AuditLog.action == "user.password_changed")
    )
    assert entry is not None
    assert entry.actor_login == CLI_ACTOR


async def test_reset_password_rejects_unknown_login(session: AsyncSession) -> None:
    result = await _invoke(["reset-password", "nobody"])

    assert result.exit_code == 1
    assert "nobody" in result.output
