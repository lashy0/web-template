from collections.abc import Callable
from uuid import UUID

from loguru import logger
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.auth.exceptions import OAuthClientNotFoundError
from app.shared.security import CurrentPrincipal

from ..audit import audit_actor, audit_entity
from ..contracts import PakOAuthClientPort, PakVerificationHistoryPort
from ..crypto import PakAccessKeyCipher
from ..exceptions import (
    PakCannotBeDeletedError,
    PakDeletionSynchronizationError,
)
from ..queries import PakQueries
from ..repository import PakRepository


class DeletePak:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        oauth: PakOAuthClientPort,
        verification_history_factory: Callable[[AsyncSession], PakVerificationHistoryPort],
        access_key_encryption_key: SecretStr | None,
    ) -> None:
        self._session_factory = session_factory
        self._oauth = oauth
        self._verification_history_factory = verification_history_factory
        self._access_key_encryption_key = access_key_encryption_key

    async def execute(self, *, actor: CurrentPrincipal, pak_id: UUID) -> None:
        oauth_client_deleted = False
        oauth_client_id: str | None = None
        encrypted_access_key: str | None = None
        try:
            async with self._session_factory() as session, session.begin():
                repository = PakRepository(session)
                pak = await PakQueries(self._session_factory).require(repository, pak_id)
                if await self._verification_history_factory(session).has_history_for_pak(pak.id):
                    raise PakCannotBeDeletedError
                oauth_client_id, encrypted_access_key = (
                    pak.oauth_client_id,
                    pak.encrypted_access_key,
                )
                try:
                    async with session.begin_nested():
                        try:
                            await self._oauth.delete_client(oauth_client_id)
                            oauth_client_deleted = True
                        except OAuthClientNotFoundError:
                            pass
                        await TransactionalAuditWriter.from_session(session).record(
                            actor=audit_actor(actor),
                            action="pak.deleted",
                            entity=audit_entity(pak),
                            old_data={
                                "pak_id": str(pak.id),
                                "code": pak.code,
                                "oauth_client_id": pak.oauth_client_id,
                            },
                        )
                        await repository.delete(pak)
                except Exception as exc:
                    if not oauth_client_deleted:
                        raise
                    await self._restore(oauth_client_id, encrypted_access_key, pak_id)
                    oauth_client_deleted = False
                    raise PakDeletionSynchronizationError from exc
        except Exception as exc:
            if not oauth_client_deleted or oauth_client_id is None or encrypted_access_key is None:
                raise
            await self._restore(oauth_client_id, encrypted_access_key, pak_id)
            logger.bind(
                event="pak.deletion_synchronization_failed",
                pak_id=str(pak_id),
                oauth_client_id=oauth_client_id,
                error_type=type(exc).__name__,
            ).opt(exception=exc).critical("Local PAK deletion failed after OAuth client deletion")
            raise PakDeletionSynchronizationError from exc

    async def _restore(self, oauth_client_id: str, encrypted_access_key: str, pak_id: UUID) -> None:
        try:
            await self._oauth.create_client(
                client_id=oauth_client_id,
                client_secret=self._cipher().decrypt(encrypted_access_key),
            )
        except Exception as exc:
            logger.bind(
                event="pak.deletion_compensation_failed",
                pak_id=str(pak_id),
                oauth_client_id=oauth_client_id,
                error_type=type(exc).__name__,
            ).opt(exception=exc).critical(
                "Hydra OAuth client could not be restored after local deletion failed"
            )
        else:
            logger.bind(
                event="pak.deletion_compensated",
                pak_id=str(pak_id),
                oauth_client_id=oauth_client_id,
            ).error("Hydra OAuth client was restored after local deletion failed")

    def _cipher(self) -> PakAccessKeyCipher:
        key = (
            self._access_key_encryption_key.get_secret_value()
            if self._access_key_encryption_key
            else None
        )
        return PakAccessKeyCipher(key)
