"""Command-line tasks of the accounts domain.

Operators run them from the host through ``otk`` (``infrastructure/cli/otk.py``),
which executes ``python -m app.otk`` in the running API container.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

import anyio
import click

from app.config import get_settings
from app.db.enums import UserRole
from app.domain.accounts.schemas import UserCreate
from app.domain.accounts.services import UserService
from app.domain.admin.services import AuditLogService
from app.lib.exceptions import ApplicationError
from app.lib.kratos import KratosClient
from app.lib.uow import UnitOfWork, unit_of_work
from app.lib.validation import generate_password

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from app.db import models as m

CLI_ACTOR = "cli"
"""``actor_login`` of the audit entries written by these commands."""
ADMIN_LOGIN = "admin"
ADMIN_NAME = "Администратор"
"""Login and name of the administrator ``ensure-admin`` creates."""


@dataclass(frozen=True, slots=True)
class _Accounts:
    users: UserService
    audit: AuditLogService
    uow: UnitOfWork
    kratos: KratosClient


@asynccontextmanager
async def _accounts() -> AsyncGenerator[_Accounts]:
    """Open the services of one command; the changes commit when the block exits."""
    settings = get_settings()
    alchemy = settings.db.get_config()
    kratos = KratosClient(
        base_url=settings.kratos.admin_url,
        timeout=settings.kratos.admin_timeout,
        concurrency=settings.kratos.admin_concurrency,
    )

    try:
        async with (
            alchemy.get_session() as db_session,
            unit_of_work(db_session) as uow,
            UserService.new(session=db_session) as users,
            AuditLogService.new(session=db_session) as audit,
        ):
            yield _Accounts(users=users, audit=audit, uow=uow, kratos=kratos)
    finally:
        await alchemy.get_engine().dispose()


@click.group(name="users", help="Manage application users.")
def users_group() -> None:
    """Group of the user commands."""


@users_group.command(name="create", help="Create a user with a password entered at a prompt.")
@click.option("--login", prompt="Login", help="Sign-in login.")
@click.option("--name", prompt="Name", help="Display name.")
@click.option(
    "--role",
    type=click.Choice([role.value for role in UserRole]),
    prompt="Role",
    help="Role of the user.",
)
def create_user(login: str, name: str, role: str) -> None:
    # Only prompted, so the password never lands in the shell history.
    password: str = click.prompt("Password", hide_input=True, confirmation_prompt=True)

    try:
        data = UserCreate(login=login, name=name, role=UserRole(role), password=password)
        user = anyio.run(_create_user, data)
    except ApplicationError as error:
        raise click.ClickException(error.detail) from error

    click.echo(f"Created the user {user.identity_login!r} ({user.role.value}).")


@users_group.command(
    name="ensure-admin",
    help=(
        f"Create the administrator {ADMIN_LOGIN!r} with a generated password unless an active "
        "administrator exists. Prints nothing when there is one."
    ),
)
def ensure_admin() -> None:
    password = generate_password()

    try:
        data = UserCreate(
            login=ADMIN_LOGIN,
            name=ADMIN_NAME,
            role=UserRole.ADMINISTRATOR,
            password=password,
        )
        created = anyio.run(_ensure_admin, data)
    except ApplicationError as error:
        raise click.ClickException(error.detail) from error

    # Silent otherwise: ``infra up`` shows whatever this command prints.
    if created:
        click.echo(f"Created the administrator: login {ADMIN_LOGIN}, password {password}")
        click.echo(f"The password is shown only once; replace it with: otk users reset-password {ADMIN_LOGIN}")


@users_group.command(
    name="reset-password",
    help="Replace the password of a user with a generated one and end their sessions.",
)
@click.argument("login")
def reset_password(login: str) -> None:
    password = generate_password()

    try:
        user = anyio.run(_reset_password, login.strip().lower(), password)
    except ApplicationError as error:
        raise click.ClickException(error.detail) from error

    click.echo(f"New password of {user.identity_login!r}: {password}")


async def _create_user(data: UserCreate) -> m.User:
    async with _accounts() as accounts:
        return await _create(accounts, data)


async def _ensure_admin(data: UserCreate) -> bool:
    async with _accounts() as accounts:
        if await accounts.users.has_active_administrator():
            return False

        await _create(accounts, data)

        return True


async def _create(accounts: _Accounts, data: UserCreate) -> m.User:
    user = await accounts.users.create_user(data, kratos=accounts.kratos, uow=accounts.uow)
    await accounts.audit.log_action(
        action="user.created",
        actor_login=CLI_ACTOR,
        target=user,
        details={"role": data.role.value, "is_active": data.is_active},
    )

    return user


async def _reset_password(login: str, password: str) -> m.User:
    async with _accounts() as accounts:
        user = await accounts.users.get_one_or_none(identity_login=login)

        if user is None:
            msg = f"No user has the login {login!r}."
            raise click.ClickException(msg)

        await accounts.users.set_password(user.id, password, kratos=accounts.kratos)
        await accounts.audit.log_action(
            action="user.password_changed",
            actor_login=CLI_ACTOR,
            target=user,
        )

        return user


__all__ = ("users_group",)
