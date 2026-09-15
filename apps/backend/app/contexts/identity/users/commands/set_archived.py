from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..audit import audit_actor, audit_entity
from ..contracts import UserIdentityProviderPort
from ..model import User
from ..queries import required_user
from ..repository import UserRepository
from ..rules import ensure_not_self, ensure_not_system_administrator


class SetUserArchived:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: UserIdentityProviderPort,
    ) -> None:
        self._session_factory, self._identities = session_factory, identities

    async def execute(self, *, actor: CurrentPrincipal, user_id: UUID, archived: bool) -> User:
        ensure_not_system_administrator(user_id)
        if not archived:
            async with self._session_factory() as session, session.begin():
                repository = UserRepository(session)
                user = await required_user(repository, user_id)
                if user.archived_at is None:
                    return user
                user = await repository.update_archived(user, archived_at=None)
                await TransactionalAuditWriter.from_session(session).record(
                    actor=audit_actor(actor),
                    action="user.restored",
                    entity=audit_entity(user),
                    new_data={"name": user.name, "login": user.identity_login},
                )
                return user
        async with self._session_factory() as session, session.begin():
            repository = UserRepository(session)
            user = await required_user(repository, user_id)
            if user.archived_at is not None:
                return user
            ensure_not_self(actor, user, action="archive")
            identity = await self._identities.set_active(user.identity_id, active=False)
            archived_at = datetime.now(UTC)
            user = await required_user(repository, user_id)
            user = await repository.update_identity_projection(
                user, login=identity.login, state="inactive", synced_at=archived_at
            )
            user = await repository.update_archived(user, archived_at=archived_at)
            await TransactionalAuditWriter.from_session(session).record(
                actor=audit_actor(actor),
                action="user.archived",
                entity=audit_entity(user),
                new_data={"name": user.name, "login": user.identity_login},
            )
        await self._identities.revoke_all_sessions(user.identity_id)
        return user
