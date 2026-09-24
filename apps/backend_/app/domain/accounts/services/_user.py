from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from uuid import UUID

import msgspec
from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import select
from uuid_utils.compat import uuid7

from app.db import models as m
from app.db.enums import UserRole
from app.domain.accounts import schemas as s
from app.domain.accounts.exceptions import (
    LastAdministratorError,
    SelfActionForbiddenError,
    UserArchivedError,
)
from app.lib.kratos import KratosClient
from app.lib.uow import UnitOfWork


class UserService(service.SQLAlchemyAsyncRepositoryService[m.User]):
    """Handles database operations for users."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.User]):
        """User SQLAlchemy Repository."""

        model_type = m.User

    repository_type = Repo

    async def create_user(
        self,
        data: s.UserCreate,
        *,
        kratos: KratosClient,
        uow: UnitOfWork,
    ) -> m.User:
        user_id = uuid7()

        # Authentication also requires the local user, so an active identity
        # grants nothing until this transaction commits.
        identity = await kratos.create_identity(
            user_id=user_id,
            login=data.login,
            password=data.password,
            is_active=data.is_active,
        )
        # Not needed for safety; frees the login so the request can be retried.
        uow.on_rollback("user.create.rollback", partial(kratos.delete_identity, identity.id))

        return await self.create(
            data={
                "id": user_id,
                "identity_id": identity.id,
                "identity_login": identity.login,
                "identity_active": identity.is_active,
                "name": data.name,
                "role": data.role,
            },
            auto_commit=False,
        )

    async def update_user(
        self,
        user_id: UUID,
        data: s.UserUpdate,
        *,
        kratos: KratosClient,
        uow: UnitOfWork,
    ) -> m.User:
        user = await self.get(user_id)

        self._ensure_not_archived(user)

        if data.login is not msgspec.UNSET and data.login != user.identity_login:
            # Kratos owns the login used to sign in; the column is a copy.
            identity = await kratos.update_login(user.identity_id, login=data.login)
            uow.on_rollback(
                "user.update.rollback",
                partial(kratos.update_login, user.identity_id, login=user.identity_login),
            )
            user.identity_login = identity.login

        if data.name is not msgspec.UNSET:
            user.name = data.name

        await self.repository.session.flush()

        return user

    async def assign_role(
        self,
        user_id: UUID,
        role: UserRole,
        *,
        actor_id: UUID | None = None,
    ) -> m.User:
        user = await self.get(user_id)

        self._ensure_not_archived(user)

        if user.role == role:
            return user

        if user.role == UserRole.ADMINISTRATOR:
            self._ensure_not_self(user, actor_id, "You cannot remove your own administrator role.")
            await self._ensure_administrator_remains(user)

        user.role = role

        await self.repository.session.flush()

        return user

    async def update_profile(self, user_id: UUID, data: s.ProfileUpdate) -> m.User:
        user = await self.get(user_id)

        self._ensure_not_archived(user)

        if data.name is not msgspec.UNSET:
            user.name = data.name

        await self.repository.session.flush()

        return user

    async def set_password(
        self,
        user_id: UUID,
        password: str,
        *,
        kratos: KratosClient,
    ) -> m.User:
        user = await self.get(user_id)

        self._ensure_not_archived(user)

        await kratos.set_password(user.identity_id, password=password)
        await kratos.revoke_all_sessions(user.identity_id)

        return user

    async def set_active(
        self,
        user_id: UUID,
        *,
        is_active: bool,
        kratos: KratosClient,
        uow: UnitOfWork,
        actor_id: UUID | None = None,
    ) -> m.User:
        user = await self.get(user_id)

        self._ensure_not_archived(user)

        if is_active:
            # Grants access: fail the request before anything is committed.
            await kratos.set_active(user.identity_id, is_active=True)
        else:
            if user.identity_active:
                self._ensure_not_self(user, actor_id, "You cannot deactivate your own account.")
                await self._ensure_administrator_remains(user)

            # Revokes access: the committed local flag already denies it.
            self._deactivate_identity_after_commit(user, kratos=kratos, uow=uow)

        user.identity_active = is_active

        await self.repository.session.flush()

        return user

    async def set_archived(
        self,
        user_id: UUID,
        *,
        archived: bool,
        kratos: KratosClient,
        uow: UnitOfWork,
        actor_id: UUID | None = None,
    ) -> m.User:
        user = await self.get(user_id)

        if not archived:
            user.archived_at = None
            await self.repository.session.flush()

            return user

        if user.archived_at is None:
            self._ensure_not_self(user, actor_id, "You cannot archive your own account.")
            await self._ensure_administrator_remains(user)
            user.archived_at = datetime.now(UTC)

        user.identity_active = False
        self._deactivate_identity_after_commit(user, kratos=kratos, uow=uow)

        await self.repository.session.flush()

        return user

    async def delete_user(
        self,
        user_id: UUID,
        *,
        kratos: KratosClient,
        uow: UnitOfWork,
        actor_id: UUID | None = None,
    ) -> m.User:
        user = await self.get(user_id)

        self._ensure_not_self(user, actor_id, "You cannot delete your own account.")
        await self._ensure_administrator_remains(user)

        await self.repository.session.delete(user)
        await self.repository.session.flush()
        uow.after_commit("user.delete", partial(kratos.delete_identity, user.identity_id))

        return user

    @staticmethod
    def _deactivate_identity_after_commit(
        user: m.User,
        *,
        kratos: KratosClient,
        uow: UnitOfWork,
    ) -> None:
        uow.after_commit(
            "user.deactivate",
            partial(kratos.set_active, user.identity_id, is_active=False),
        )
        uow.after_commit(
            "user.deactivate.sessions",
            partial(kratos.revoke_all_sessions, user.identity_id),
        )

    @staticmethod
    def _ensure_not_archived(user: m.User) -> None:
        if user.archived_at is not None:
            raise UserArchivedError

    @staticmethod
    def _ensure_not_self(
        user: m.User,
        actor_id: UUID | None,
        detail: str,
    ) -> None:
        if actor_id is not None and user.id == actor_id:
            raise SelfActionForbiddenError(detail=detail)

    async def _ensure_administrator_remains(self, user: m.User) -> None:
        if not _is_active_administrator(user):
            return

        administrator_ids = await self.repository.session.scalars(
            select(m.User.id)
            .where(
                m.User.role == UserRole.ADMINISTRATOR,
                m.User.identity_active.is_(True),
                m.User.archived_at.is_(None),
            )
            .order_by(m.User.id)
            .with_for_update()
        )

        if not any(administrator_id != user.id for administrator_id in administrator_ids):
            raise LastAdministratorError


def _is_active_administrator(user: m.User) -> bool:
    return (
        user.role == UserRole.ADMINISTRATOR
        and user.identity_active
        and user.archived_at is None
    )
