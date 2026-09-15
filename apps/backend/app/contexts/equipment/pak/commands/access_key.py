from uuid import UUID

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..audit import audit_actor, audit_entity
from ..crypto import PakAccessKeyCipher
from ..queries import PakQueries
from ..repository import PakRepository


class GetPakAccessKey:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        access_key_encryption_key: SecretStr | None,
    ) -> None:
        self._session_factory = session_factory
        self._access_key_encryption_key = access_key_encryption_key

    async def execute(self, *, actor: CurrentPrincipal, pak_id: UUID) -> str:
        async with self._session_factory() as session, session.begin():
            pak = await PakQueries(self._session_factory).require(PakRepository(session), pak_id)
            access_key = self._cipher().decrypt(pak.encrypted_access_key)
            await TransactionalAuditWriter.from_session(session).record(
                actor=audit_actor(actor),
                action="pak.access_key_viewed",
                entity=audit_entity(pak),
                new_data={
                    "pak_id": str(pak.id),
                    "code": pak.code,
                    "oauth_client_id": pak.oauth_client_id,
                },
            )
            return access_key

    def _cipher(self) -> PakAccessKeyCipher:
        key = (
            self._access_key_encryption_key.get_secret_value()
            if self._access_key_encryption_key
            else None
        )
        return PakAccessKeyCipher(key)
