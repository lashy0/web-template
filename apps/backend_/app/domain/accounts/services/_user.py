from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import msgspec
from advanced_alchemy.extensions.litestar import repository, service
from loguru import logger
from uuid_utils.compat import uuid7

from app.db import models as m
from app.domain.accounts import schemas as s
from app.lib.deps import CompositeServiceMixin
from app.lib.exceptions import ApplicationClientError
from app.lib.kratos import KratosClient
from app.lib.kratos.exceptions import KratosIdentityNotFoundError
from app.lib.kratos.schemas import KratosIdentity


class UserService(CompositeServiceMixin, service.SQLAlchemyAsyncRepositoryService[m.User]):
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
    ) -> m.User:
        user_id = uuid7()

        identity = await kratos.create_identity(
            user_id=user_id,
            login=data.login,
            password=data.password,
            # Identity must not become usable before DB user exists.
            is_active=False,
        )

        try:
            user = await self.create(
                data={
                    "id": user_id,
                    "identity_id": identity.id,
                    "identity_login": identity.login,
                    "identity_active": False,
                    "name": data.name,
                    "role": data.role,
                },
                auto_commit=False,
            )

            await self.repository.session.commit()

        except Exception:
            await self.repository.session.rollback()

            await self._delete_identity_safely(
                identity.id,
                kratos=kratos,
                operation="user.create",
            )

            raise

        if data.is_active:
            try:
                await kratos.set_active(
                    identity.id,
                    is_active=True,
                )

                user.identity_active = True

                await self.repository.session.flush()

            except Exception:
                logger.bind(
                    user_id=str(user.id),
                    identity_id=str(identity.id),
                ).exception("User created but Kratos identity activation failed")

                raise

        return user

    async def update_user(
        self,
        user_id: UUID,
        data: s.UserUpdate,
        *,
        kratos: KratosClient,
    ) -> m.User:
        user = await self.get(user_id)

        self._ensure_not_archived(user)

        old_login = user.identity_login
        login_changed = False

        try:
            if data.login is not msgspec.UNSET and data.login != user.identity_login:
                identity = await kratos.update_login(
                    user.identity_id,
                    login=data.login,
                )

                user.identity_login = identity.login
                login_changed = True

            if data.name is not msgspec.UNSET:
                user.name = data.name

            if data.role is not msgspec.UNSET:
                user.role = data.role

            await self.repository.session.flush()
            await self.repository.session.commit()

        except Exception:
            await self.repository.session.rollback()

            if login_changed:
                await self._restore_login_safely(
                    identity_id=user.identity_id,
                    login=old_login,
                    kratos=kratos,
                )

            raise

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
    ) -> None:
        user = await self.get(user_id)

        self._ensure_not_archived(user)

        await kratos.set_password(
            user.identity_id,
            password=password,
        )

        await kratos.revoke_all_sessions(user.identity_id)

    async def set_active(
        self,
        user_id: UUID,
        *,
        is_active: bool,
        kratos: KratosClient,
    ) -> m.User:
        user = await self.get(user_id)

        self._ensure_not_archived(user)

        identity = await kratos.get_identity(user.identity_id)

        if identity.is_active == is_active:
            return user

        await kratos.set_active(
            user.identity_id,
            is_active=is_active,
        )

        user.identity_active = is_active

        await self.repository.session.flush()

        if not is_active:
            await kratos.revoke_all_sessions(user.identity_id)

        return user

    async def set_archived(
        self,
        user_id: UUID,
        *,
        archived: bool,
        kratos: KratosClient,
    ) -> m.User:
        user = await self.get(user_id)

        currently_archived = user.archived_at is not None

        if currently_archived == archived:
            return user

        if not archived:
            user.archived_at = None
            await self.repository.session.flush()

            return user

        identity = await kratos.get_identity(user.identity_id)

        was_active = identity.is_active

        if was_active:
            await kratos.set_active(
                user.identity_id,
                is_active=False,
            )

        try:
            user.archived_at = datetime.now(UTC)

            await self.repository.session.flush()
            await self.repository.session.commit()

        except Exception:
            await self.repository.session.rollback()

            if was_active:
                await self._set_active_safely(
                    identity_id=user.identity_id,
                    is_active=True,
                    kratos=kratos,
                    operation="user.archive.rollback",
                )

            raise

        await kratos.revoke_all_sessions(user.identity_id)

        return user

    async def delete_user(self, user_id: UUID, *, kratos: KratosClient) -> None:
        user = await self.get(user_id)

        identity: KratosIdentity | None

        try:
            identity = await kratos.get_identity(user.identity_id)

        except KratosIdentityNotFoundError:
            identity = None

        if identity is not None:
            if identity.is_active:
                await kratos.set_active(
                    identity.id,
                    is_active=False,
                )

            await kratos.revoke_all_sessions(identity.id)

        try:
            await self.repository.session.delete(user)
            await self.repository.session.commit()

        except Exception:
            await self.repository.session.rollback()

            if identity is not None and identity.is_active:
                await self._set_active_safely(
                    identity_id=identity.id,
                    is_active=True,
                    kratos=kratos,
                    operation="user.delete.rollback",
                )

            raise

        if identity is not None:
            await self._delete_identity_safely(
                identity.id,
                kratos=kratos,
                operation="user.delete",
            )

    @staticmethod
    def _ensure_not_archived(user: m.User) -> None:
        if user.archived_at is not None:
            raise ApplicationClientError(
                detail="Archived user cannot be modified.",
            )

    async def _rollback_created_user(
        self,
        *,
        user: m.User,
        identity_id: UUID,
        kratos: KratosClient,
    ) -> None:
        await self._delete_identity_safely(
            identity_id,
            kratos=kratos,
            operation="user.create.rollback",
        )

        try:
            await self.repository.session.delete(user)
            await self.repository.session.commit()

        except Exception:
            await self.repository.session.rollback()

            logger.bind(
                operation="user.create.rollback",
                user_id=str(user.id),
                identity_id=str(identity_id),
            ).exception("Failed to roll back database user")

    async def _delete_identity_safely(
        self,
        identity_id: UUID,
        *,
        kratos: KratosClient,
        operation: str,
    ) -> None:
        try:
            await kratos.delete_identity(identity_id)

        except Exception:
            logger.bind(
                operation=operation,
                identity_id=str(identity_id),
            ).exception("Failed to delete Kratos identity")

    async def _restore_login_safely(
        self,
        *,
        identity_id: UUID,
        login: str,
        kratos: KratosClient,
    ) -> None:
        try:
            await kratos.update_login(
                identity_id,
                login=login,
            )

        except Exception:
            logger.bind(
                operation="user.update.rollback",
                identity_id=str(identity_id),
                login=login,
            ).exception("Failed to restore Kratos login")

    async def _set_active_safely(
        self,
        *,
        identity_id: UUID,
        is_active: bool,
        kratos: KratosClient,
        operation: str,
    ) -> None:
        try:
            await kratos.set_active(
                identity_id,
                is_active=is_active,
            )

        except Exception:
            logger.bind(
                operation=operation,
                identity_id=str(identity_id),
                is_active=is_active,
            ).exception("Failed to restore Kratos identity state")
