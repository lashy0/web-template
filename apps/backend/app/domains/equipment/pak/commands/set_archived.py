from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..audit import audit_actor, audit_entity
from ..model import PakDevice
from ..queries import PakQueries
from ..repository import PakRepository


class SetPakArchived:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def execute(self, *, actor: CurrentPrincipal, pak_id: UUID, archived: bool) -> PakDevice:
        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)
            pak = await PakQueries(self._session_factory).require(repository, pak_id)
            if not archived:
                if pak.archived_at is None:
                    return pak
                pak = await repository.update_archived(pak, archived_at=None)
                action = "pak.restored"
            else:
                if pak.archived_at is not None:
                    return pak
                if pak.is_active:
                    pak = await repository.update_active(pak, active=False)
                pak = await repository.update_archived(pak, archived_at=datetime.now(UTC))
                action = "pak.archived"
            await TransactionalAuditWriter.from_session(session).record(
                actor=audit_actor(actor), action=action, entity=audit_entity(pak)
            )
            return pak
