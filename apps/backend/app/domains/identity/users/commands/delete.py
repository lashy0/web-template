from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..audit import audit_actor, audit_entity
from ..contracts import UserIdentityProviderPort
from ..queries import required_user
from ..repository import UserRepository
from ..rules import ensure_not_self, ensure_not_system_administrator


class DeleteUser:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: UserIdentityProviderPort,
    ) -> None:
        self._session_factory, self._identities = session_factory, identities

    async def execute(self, *, actor: CurrentPrincipal, user_id: UUID) -> None:
        ensure_not_system_administrator(user_id)
        async with self._session_factory() as session, session.begin():
            repository = UserRepository(session)
            user = await required_user(repository, user_id)
            ensure_not_self(actor, user, action="delete")
            await self._identities.delete_identity(user.identity_id)
            user = await required_user(repository, user_id)
            await TransactionalAuditWriter.from_session(session).record(
                actor=audit_actor(actor),
                action="user.deleted",
                entity=audit_entity(user),
                old_data={"name": user.name, "role": user.role.value, "login": user.identity_login},
            )
            await repository.delete(user)
