from uuid import UUID

from loguru import logger
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import OAuthClientManager
from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService

from ..crypto import PakAccessKeyCipher
from ..exceptions import (
    PakCredentialSynchronizationError,
    PakProvisioningError,
)
from ..repository import PakRepository
from .audit import _audit_actor, _audit_entity
from .lifecycle import _ensure_not_archived
from .queries import _required_pak


class PakCredentialService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        oauth_clients: OAuthClientManager,
        access_key_encryption_key: SecretStr | None,
    ) -> None:
        self._session_factory = session_factory
        self._oauth_clients = oauth_clients
        self._access_key_encryption_key = access_key_encryption_key

    async def get_access_key(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
    ) -> str:
        async with self._session_factory() as session, session.begin():
            pak = await _required_pak(PakRepository(session), pak_id)
            access_key = self._cipher().decrypt(pak.encrypted_access_key)

            await AuditService.from_session(session).record(
                actor=_audit_actor(actor),
                action="pak.access_key_viewed",
                entity=_audit_entity(pak),
                new_data={
                    "pak_id": str(pak.id),
                    "code": pak.code,
                    "oauth_client_id": pak.oauth_client_id,
                },
            )

            return access_key

    async def rotate_access_key(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
    ) -> str:
        rotated = False
        oauth_client_id: str | None = None
        previous_client_secret: str | None = None
        new_access_key: str | None = None

        try:
            async with self._session_factory() as session, session.begin():
                repository = PakRepository(session)
                pak = await _required_pak(repository, pak_id)

                _ensure_not_archived(pak)

                oauth_client_id = pak.oauth_client_id
                cipher = self._cipher()
                previous_client_secret = cipher.decrypt(pak.encrypted_access_key)

                try:
                    async with session.begin_nested():
                        credentials = await self._oauth_clients.rotate_client_credentials(
                            oauth_client_id
                        )
                        rotated = True
                        new_access_key = credentials.client_secret

                        if credentials.client.client_id != oauth_client_id:
                            raise PakProvisioningError(
                                "OAuth provider changed the PAK client ID during rotation"
                            )

                        pak = await repository.update_access_key(
                            pak, encrypted_access_key=cipher.encrypt(credentials.client_secret)
                        )

                        await AuditService.from_session(session).record(
                            actor=_audit_actor(actor),
                            action="pak.access_key_rotated",
                            entity=_audit_entity(pak),
                            new_data={
                                "pak_id": str(pak.id),
                                "code": pak.code,
                                "oauth_client_id": pak.oauth_client_id,
                            },
                        )

                except Exception as exc:
                    if not rotated or oauth_client_id is None or previous_client_secret is None:
                        raise

                    await self._restore_secret(
                        pak_id=pak_id,
                        oauth_client_id=oauth_client_id,
                        previous_client_secret=previous_client_secret,
                        exc=exc,
                    )

                    rotated = False

                    raise PakCredentialSynchronizationError from exc

        except Exception as exc:
            if not rotated or oauth_client_id is None or previous_client_secret is None:
                raise

            await self._restore_secret(
                pak_id=pak_id,
                oauth_client_id=oauth_client_id,
                previous_client_secret=previous_client_secret,
                exc=exc,
            )

            raise PakCredentialSynchronizationError from exc

        if new_access_key is None:
            raise PakProvisioningError("OAuth provider did not return a PAK client secret")

        return new_access_key

    def _cipher(self) -> PakAccessKeyCipher:
        key = (
            self._access_key_encryption_key.get_secret_value()
            if self._access_key_encryption_key is not None
            else None
        )

        return PakAccessKeyCipher(key)

    async def _restore_secret(
        self,
        *,
        pak_id: UUID,
        oauth_client_id: str,
        previous_client_secret: str,
        exc: Exception,
    ) -> None:
        try:
            restored = await self._oauth_clients.set_client_secret(
                oauth_client_id, previous_client_secret
            )

            if restored.client.client_id != oauth_client_id:
                raise PakProvisioningError("Hydra changed the PAK client ID during compensation")

        except Exception as compensation_error:
            logger.bind(
                event="pak.credentials_synchronization_failed",
                pak_id=str(pak_id),
                oauth_client_id=oauth_client_id,
                error_type=type(exc).__name__,
                compensation_error_type=type(compensation_error).__name__,
            ).opt(exception=compensation_error).critical(
                "Hydra credentials were rotated but the encrypted local copy was not saved"
            )

        else:
            logger.bind(
                event="pak.credentials_rotation_compensated",
                pak_id=str(pak_id),
                oauth_client_id=oauth_client_id,
                error_type=type(exc).__name__,
            ).error("Hydra credential rotation was reverted after the local update failed")
