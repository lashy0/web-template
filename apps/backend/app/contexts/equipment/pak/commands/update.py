from uuid import UUID

from loguru import logger
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..audit import audit_actor, audit_entity
from ..contracts import PakOAuthClientPort
from ..crypto import PakAccessKeyCipher
from ..exceptions import (
    PakAlreadyExistsError,
    PakCredentialSynchronizationError,
    PakProvisioningError,
)
from ..model import PakDevice, PakDeviceKind
from ..queries import PakQueries
from ..repository import PakRepository
from ..rules import ensure_not_archived


class UpdatePak:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def execute(
        self, *, actor: CurrentPrincipal, pak_id: UUID, code: str | None, kind: PakDeviceKind | None
    ) -> PakDevice:
        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)
            pak = await PakQueries(self._session_factory).require(repository, pak_id)
            ensure_not_archived(pak)
            old_values = {"code": pak.code, "kind": pak.kind.value}
            if code is not None and code != pak.code:
                existing = await repository.get_by_code(code)
                if existing is not None and existing.id != pak.id:
                    raise PakAlreadyExistsError
            try:
                pak = await repository.update_details(pak, code=code, kind=kind)
            except IntegrityError as exc:
                raise PakAlreadyExistsError from exc
            new_values = {"code": pak.code, "kind": pak.kind.value}
            changed = {key: value for key, value in new_values.items() if value != old_values[key]}
            if changed:
                await TransactionalAuditWriter.from_session(session).record(
                    actor=audit_actor(actor),
                    action="pak.updated",
                    entity=audit_entity(pak),
                    old_data={key: old_values[key] for key in changed},
                    new_data=changed,
                )
            return pak


class SetPakActive:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def execute(self, *, actor: CurrentPrincipal, pak_id: UUID, active: bool) -> PakDevice:
        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)
            pak = await PakQueries(self._session_factory).require(repository, pak_id)
            ensure_not_archived(pak)
            if pak.is_active == active:
                return pak
            old_active = pak.is_active
            pak = await repository.update_active(pak, active=active)
            await TransactionalAuditWriter.from_session(session).record(
                actor=audit_actor(actor),
                action="pak.active_changed",
                entity=audit_entity(pak),
                old_data={"active": old_active},
                new_data={"active": active},
            )
            return pak


class RotatePakAccessKey:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        oauth: PakOAuthClientPort,
        access_key_encryption_key: SecretStr | None,
    ) -> None:
        self._session_factory, self._oauth, self._access_key_encryption_key = (
            session_factory,
            oauth,
            access_key_encryption_key,
        )

    async def execute(self, *, actor: CurrentPrincipal, pak_id: UUID) -> str:
        rotated = False
        oauth_client_id: str | None = None
        previous_client_secret: str | None = None
        new_access_key: str | None = None
        try:
            async with self._session_factory() as session, session.begin():
                repository = PakRepository(session)
                pak = await PakQueries(self._session_factory).require(repository, pak_id)
                ensure_not_archived(pak)
                oauth_client_id = pak.oauth_client_id
                cipher = self._cipher()
                previous_client_secret = cipher.decrypt(pak.encrypted_access_key)
                try:
                    async with session.begin_nested():
                        credentials = await self._oauth.rotate_client_credentials(oauth_client_id)
                        rotated, new_access_key = True, credentials.client_secret
                        if credentials.client.client_id != oauth_client_id:
                            raise PakProvisioningError(
                                "OAuth provider changed the PAK client ID during rotation"
                            )
                        pak = await repository.update_access_key(
                            pak, encrypted_access_key=cipher.encrypt(credentials.client_secret)
                        )
                        await TransactionalAuditWriter.from_session(session).record(
                            actor=audit_actor(actor),
                            action="pak.access_key_rotated",
                            entity=audit_entity(pak),
                            new_data={
                                "pak_id": str(pak.id),
                                "code": pak.code,
                                "oauth_client_id": pak.oauth_client_id,
                            },
                        )
                except Exception as exc:
                    if not rotated or oauth_client_id is None or previous_client_secret is None:
                        raise
                    await self._restore(oauth_client_id, previous_client_secret, pak_id, exc)
                    rotated = False
                    raise PakCredentialSynchronizationError from exc
        except Exception as exc:
            if not rotated or oauth_client_id is None or previous_client_secret is None:
                raise
            await self._restore(oauth_client_id, previous_client_secret, pak_id, exc)
            raise PakCredentialSynchronizationError from exc
        if new_access_key is None:
            raise PakProvisioningError("OAuth provider did not return a PAK client secret")
        return new_access_key

    async def _restore(
        self, client_id: str, secret: str, pak_id: UUID, original: Exception
    ) -> None:
        try:
            restored = await self._oauth.set_client_secret(client_id, secret)
            if restored.client.client_id != client_id:
                raise PakProvisioningError("Hydra changed the PAK client ID during compensation")
        except Exception as compensation_error:
            logger.bind(
                event="pak.credentials_synchronization_failed",
                pak_id=str(pak_id),
                oauth_client_id=client_id,
                error_type=type(original).__name__,
                compensation_error_type=type(compensation_error).__name__,
            ).opt(exception=compensation_error).critical(
                "Hydra credentials were rotated but the encrypted local copy was not saved"
            )
        else:
            logger.bind(
                event="pak.credentials_rotation_compensated",
                pak_id=str(pak_id),
                oauth_client_id=client_id,
                error_type=type(original).__name__,
            ).error("Hydra credential rotation was reverted after the local update failed")

    def _cipher(self) -> PakAccessKeyCipher:
        key = (
            self._access_key_encryption_key.get_secret_value()
            if self._access_key_encryption_key
            else None
        )
        return PakAccessKeyCipher(key)
