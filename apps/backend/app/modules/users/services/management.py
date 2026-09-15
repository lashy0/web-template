# mypy: disable-error-code=no-untyped-def
"""Legacy thin delegate. New code must use identity.users commands and queries directly."""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.contexts.identity.users.commands import (
    BOOTSTRAP_ADMIN_USER_ID,
    BootstrapFirstAdministrator,
    CreateUser,
    DeleteUser,
    SetUserActive,
    SetUserArchived,
    SetUserPassword,
    UpdateUser,
)
from app.contexts.identity.users.contracts import UserIdentityProviderPort
from app.contexts.identity.users.queries import UserQueries
from app.contexts.identity.users.reconciliation import ReconcileUsers, ReconciliationResult


class UserManagementService:
    """Compatibility facade retained for callers outside the migrated composition root."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: UserIdentityProviderPort,
    ) -> None:
        self._queries = UserQueries(session_factory)
        self._create = CreateUser(session_factory, identities)
        self._update = UpdateUser(session_factory, identities)
        self._password = SetUserPassword(session_factory, identities)
        self._active = SetUserActive(session_factory, identities)
        self._archived = SetUserArchived(session_factory, identities)
        self._delete = DeleteUser(session_factory, identities)
        self._bootstrap = BootstrapFirstAdministrator(session_factory, identities)
        self._reconcile = ReconcileUsers(session_factory, identities)

    async def get(self, user_id: UUID):
        return await self._queries.get(user_id)

    async def list(self, **kwargs: object):
        return await self._queries.list(**kwargs)  # type: ignore[arg-type]

    async def create(self, **kwargs: object):
        return await self._create.execute(**kwargs)  # type: ignore[arg-type]

    async def update(self, **kwargs: object):
        return await self._update.execute(**kwargs)  # type: ignore[arg-type]

    async def set_password(self, **kwargs: object):
        return await self._password.execute(**kwargs)  # type: ignore[arg-type]

    async def set_active(self, **kwargs: object):
        return await self._active.execute(**kwargs)  # type: ignore[arg-type]

    async def set_archived(self, **kwargs: object):
        return await self._archived.execute(**kwargs)  # type: ignore[arg-type]

    async def delete(self, **kwargs: object):
        return await self._delete.execute(**kwargs)  # type: ignore[arg-type]

    async def bootstrap_first_administrator(
        self, *, name: str, login: str, password_loader: Callable[[], str | None]
    ):
        return await self._bootstrap.execute(
            name=name, login=login, password_loader=password_loader
        )

    async def reconcile(self) -> ReconciliationResult:
        return await self._reconcile.execute()


__all__ = ["BOOTSTRAP_ADMIN_USER_ID", "UserManagementService"]
