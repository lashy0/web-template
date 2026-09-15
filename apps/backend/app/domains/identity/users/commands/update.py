from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal, Role

from ..audit import audit_actor, audit_entity
from ..contracts import UserIdentityProviderPort
from ..model import User
from ..queries import required_user
from ..repository import UserRepository
from ..rules import (
    ensure_not_archived,
    ensure_not_self,
    ensure_not_system_administrator,
    ensure_self_administrator_role,
)


class UpdateUser:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: UserIdentityProviderPort,
    ) -> None:
        self._session_factory, self._identities = session_factory, identities

    async def execute(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
        login: str | None,
        name: str | None,
        role: Role | None,
    ) -> User:
        ensure_not_system_administrator(user_id)
        async with self._session_factory() as session, session.begin():
            repository = UserRepository(session)
            user = await required_user(repository, user_id)
            ensure_not_archived(user)
            ensure_self_administrator_role(actor, user, role)
            old = {"name": user.name, "role": user.role.value, "login": user.identity_login}
            identity = None
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
            new = {"name": user.name, "role": user.role.value, "login": user.identity_login}
            new_data = {key: value for key, value in new.items() if value != old[key]}
            if new_data:
                await TransactionalAuditWriter.from_session(session).record(
                    actor=audit_actor(actor),
                    action="user.updated",
                    entity=audit_entity(user),
                    old_data={key: old[key] for key in new_data},
                    new_data=new_data,
                )
            return user


class SetUserPassword:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: UserIdentityProviderPort,
    ) -> None:
        self._session_factory, self._identities = session_factory, identities

    async def execute(self, *, actor: CurrentPrincipal, user_id: UUID, password: str) -> None:
        ensure_not_system_administrator(user_id)
        async with self._session_factory() as session, session.begin():
            user = await required_user(UserRepository(session), user_id)
            ensure_not_archived(user)
            identity_id = user.identity_id
            await self._identities.set_password(user.identity_id, password=password)
            user = await required_user(UserRepository(session), user_id)
            await TransactionalAuditWriter.from_session(session).record(
                actor=audit_actor(actor),
                action="user.password_changed",
                entity=audit_entity(user),
                new_data={"name": user.name, "login": user.identity_login},
            )
        await self._identities.revoke_all_sessions(identity_id)


class SetUserActive:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: UserIdentityProviderPort,
    ) -> None:
        self._session_factory, self._identities = session_factory, identities

    async def execute(self, *, actor: CurrentPrincipal, user_id: UUID, active: bool) -> User:
        ensure_not_system_administrator(user_id)
        async with self._session_factory() as session, session.begin():
            repository = UserRepository(session)
            user = await required_user(repository, user_id)
            ensure_not_archived(user)
            old_active = user.auth_state == "active"
            if old_active == active:
                return user
            if not active:
                ensure_not_self(actor, user, action="deactivate")
            identity = await self._identities.set_active(user.identity_id, active=active)
            user = await required_user(repository, user_id)
            user = await repository.update_identity_projection(
                user,
                login=identity.login,
                state="active" if active else "inactive",
                synced_at=datetime.now(UTC),
            )
            await TransactionalAuditWriter.from_session(session).record(
                actor=audit_actor(actor),
                action="user.active_changed",
                entity=audit_entity(user),
                old_data={"active": old_active},
                new_data={"active": active},
            )
        if not active:
            await self._identities.revoke_all_sessions(user.identity_id)
        return user
