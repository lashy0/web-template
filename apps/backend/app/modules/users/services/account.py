import builtins
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import Identity, IdentityManager
from app.auth.exceptions import ForbiddenError, IdentityNotFoundError
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.audit.service import AuditService
from app.modules.audit.types import AuditActor

from ..models import User
from ..repository import UserRepository
from .audit import _audit_entity
from .bootstrap import BOOTSTRAP_ADMIN_USER_ID


def _ensure_not_system_administrator(user_id: UUID) -> None:
    if user_id == BOOTSTRAP_ADMIN_USER_ID:
        raise ForbiddenError("Cannot modify the system administrator")


def _ensure_not_archived(user: User) -> None:
    if user.archived_at is not None:
        raise ForbiddenError("Cannot modify an archived user")


async def _required_user(repository: UserRepository, user_id: UUID) -> User:
    user = await repository.get_by_id(user_id, for_update=True)

    if user is None:
        raise IdentityNotFoundError

    return user


class UserAccountService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: IdentityManager,
    ) -> None:
        self._session_factory = session_factory
        self._identities = identities

    async def get(self, user_id: UUID) -> User | None:
        async with self._session_factory() as session:
            return await UserRepository(session).get_by_id(user_id)

    async def list(
        self,
        *,
        q: str | None,
        role: Role | None,
        auth_state: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[builtins.list[User], int]:
        async with self._session_factory() as session:
            return await UserRepository(session).search(
                q=q,
                role=role,
                auth_state=auth_state,
                archived=archived,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
        login: str | None,
        name: str | None,
        role: Role | None,
    ) -> User:
        _ensure_not_system_administrator(user_id)

        async with self._session_factory() as session, session.begin():
            repository = UserRepository(session)

            user = await _required_user(repository, user_id)
            _ensure_not_archived(user)

            old_values = {
                "name": user.name,
                "role": user.role.value,
                "login": user.identity_login,
            }

            if role is not None and user.id == actor.user_id and role != Role.ADMINISTRATOR:
                raise ForbiddenError("Cannot remove your own administrator role")

            identity: Identity | None = None
            if login is not None and login != user.identity_login:
                identity = await self._identities.update_login(user.identity_id, login=login)

            if name is not None and name != user.name:
                await repository.update_name(user, name=name)

            if role is not None and role != user.role:
                await repository.update_role(user, role=role)

            if identity is not None:
                user = await repository.update_identity_projection(
                    user,
                    login=identity.login,
                    state="active" if identity.active else "inactive",
                    synced_at=datetime.now(UTC),
                )

            new_values = {
                "name": user.name,
                "role": user.role.value,
                "login": user.identity_login,
            }
            new_data = {key: value for key, value in new_values.items() if value != old_values[key]}

            if new_data:
                old_data = {key: old_values[key] for key in new_data}

                await AuditService.from_session(session).record(
                    actor=AuditActor.user(
                        actor.user_id,
                        name=actor.name,
                        login=actor.login,
                    ),
                    action="user.updated",
                    entity=_audit_entity(user),
                    old_data=old_data,
                    new_data=new_data,
                )

            return user

    async def set_password(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
        password: str,
    ) -> None:
        _ensure_not_system_administrator(user_id)

        async with self._session_factory() as session, session.begin():
            user = await _required_user(
                UserRepository(session),
                user_id,
            )

            _ensure_not_archived(user)

            await self._identities.set_password(
                user.identity_id,
                password=password,
            )

            await self._identities.revoke_all_sessions(
                user.identity_id,
            )

            user = await _required_user(
                UserRepository(session),
                user_id,
            )

            await AuditService.from_session(session).record(
                actor=AuditActor.user(
                    actor.user_id,
                    name=actor.name,
                    login=actor.login,
                ),
                action="user.password_changed",
                entity=_audit_entity(user),
                new_data={
                    "name": user.name,
                    "login": user.identity_login,
                },
            )

    async def set_active(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
        active: bool,
    ) -> User:
        _ensure_not_system_administrator(user_id)

        async with self._session_factory() as session, session.begin():
            user = await _required_user(UserRepository(session), user_id)
            _ensure_not_archived(user)

            old_active = user.auth_state == "active"

            if old_active == active:
                return user

            if not active:
                if user.id == actor.user_id:
                    raise ForbiddenError("Cannot deactivate yourself")

            identity = await self._identities.set_active(user.identity_id, active=active)

            user = await _required_user(UserRepository(session), user_id)
            user = await UserRepository(session).update_identity_projection(
                user,
                login=identity.login,
                state="active" if active else "inactive",
                synced_at=datetime.now(UTC),
            )

            await AuditService.from_session(session).record(
                actor=AuditActor.user(
                    actor.user_id,
                    name=actor.name,
                    login=actor.login,
                ),
                action="user.active_changed",
                entity=_audit_entity(user),
                old_data={"active": old_active},
                new_data={"active": active},
            )

        if not active:
            await self._identities.revoke_all_sessions(user.identity_id)

        return user

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
        archived: bool,
    ) -> User:
        _ensure_not_system_administrator(user_id)

        if not archived:
            async with self._session_factory() as session, session.begin():
                repository = UserRepository(session)
                user = await _required_user(repository, user_id)

                if user.archived_at is None:
                    return user

                user = await repository.update_archived(user, archived_at=None)

                await AuditService.from_session(session).record(
                    actor=AuditActor.user(
                        actor.user_id,
                        name=actor.name,
                        login=actor.login,
                    ),
                    action="user.restored",
                    entity=_audit_entity(user),
                    new_data={"name": user.name, "login": user.identity_login},
                )

                return user

        async with self._session_factory() as session, session.begin():
            repository = UserRepository(session)
            user = await _required_user(repository, user_id)

            if user.archived_at is not None:
                return user

            if user.id == actor.user_id:
                raise ForbiddenError("Cannot archive yourself")

            identity = await self._identities.set_active(user.identity_id, active=False)
            archived_at = datetime.now(UTC)

            repository = UserRepository(session)

            user = await _required_user(repository, user_id)
            user = await repository.update_identity_projection(
                user,
                login=identity.login,
                state="inactive",
                synced_at=archived_at,
            )

            user = await repository.update_archived(user, archived_at=archived_at)
            await AuditService.from_session(session).record(
                actor=AuditActor.user(
                    actor.user_id,
                    name=actor.name,
                    login=actor.login,
                ),
                action="user.archived",
                entity=_audit_entity(user),
                new_data={
                    "name": user.name,
                    "login": user.identity_login,
                },
            )

        await self._identities.revoke_all_sessions(user.identity_id)

        return user

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
    ) -> None:
        _ensure_not_system_administrator(user_id)

        async with self._session_factory() as session, session.begin():
            repository = UserRepository(session)
            user = await _required_user(repository, user_id)

            if user.id == actor.user_id:
                raise ForbiddenError("Cannot delete yourself")

            identity_id = user.identity_id

            await self._identities.delete_identity(identity_id)

            repository = UserRepository(session)
            user = await _required_user(repository, user_id)

            await AuditService.from_session(session).record(
                actor=AuditActor.user(
                    actor.user_id,
                    name=actor.name,
                    login=actor.login,
                ),
                action="user.deleted",
                entity=_audit_entity(user),
                old_data={
                    "name": user.name,
                    "role": user.role.value,
                    "login": user.identity_login,
                },
            )

            await repository.delete(user)
