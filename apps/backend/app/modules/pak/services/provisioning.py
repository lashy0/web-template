from uuid import UUID, uuid4

from loguru import logger
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import OAuthClientManager
from app.auth.exceptions import OAuthClientNotFoundError
from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService

from ..crypto import PakAccessKeyCipher
from ..enums import PakDeviceKind
from ..exceptions import (
    PakAlreadyExistsError,
    PakCannotBeDeletedError,
    PakDeletionSynchronizationError,
    PakProvisioningError,
)
from ..models import PakDevice
from ..repository import PakRepository
from .audit import _audit_actor, _audit_entity
from .queries import _required_pak


class PakProvisioningService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        oauth_clients: OAuthClientManager,
        access_key_encryption_key: SecretStr | None,
    ) -> None:
        self._session_factory = session_factory
        self._oauth_clients = oauth_clients
        self._access_key_encryption_key = access_key_encryption_key

    async def create(
        self,
        *,
        actor: CurrentPrincipal,
        code: str,
        kind: PakDeviceKind,
        active: bool,
    ) -> tuple[PakDevice, str]:
        pak_id = uuid4()
        oauth_client_id = f"pak-{pak_id}"

        async with self._session_factory() as session:
            if await PakRepository(session).get_by_code(code) is not None:
                raise PakAlreadyExistsError

        credentials = await self._oauth_clients.create_client(client_id=oauth_client_id)

        try:
            encrypted_access_key = self._cipher().encrypt(credentials.client_secret)

            async with self._session_factory() as session, session.begin():
                pak = await PakRepository(session).create(
                    pak_id=pak_id,
                    code=code,
                    kind=kind,
                    oauth_client_id=credentials.client.client_id,
                    encrypted_access_key=encrypted_access_key,
                    active=active,
                )

                await AuditService.from_session(session).record(
                    actor=_audit_actor(actor),
                    action="pak.created",
                    entity=_audit_entity(pak),
                    new_data={
                        "pak_id": str(pak.id),
                        "code": pak.code,
                        "oauth_client_id": pak.oauth_client_id,
                        "active": pak.is_active,
                    },
                )

                return pak, credentials.client_secret

        except IntegrityError as exc:
            await self._rollback_pak_creation(
                pak_id=pak_id, oauth_client_id=credentials.client.client_id
            )

            raise PakAlreadyExistsError from exc

        except Exception as exc:
            logger.bind(
                event="pak.provisioning_failed",
                pak_id=str(pak_id),
                oauth_client_id=oauth_client_id,
                error_type=type(exc).__name__,
            ).opt(exception=exc).error("PAK provisioning failed")

            await self._rollback_pak_creation(
                pak_id=pak_id, oauth_client_id=credentials.client.client_id
            )

            raise PakProvisioningError from exc

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
    ) -> None:
        from app.modules.verification.services import VerificationSessionService

        oauth_client_deleted = False
        oauth_client_id: str | None = None
        encrypted_access_key: str | None = None

        try:
            async with self._session_factory() as session, session.begin():
                repository = PakRepository(session)
                pak = await _required_pak(repository, pak_id)

                if await VerificationSessionService.has_pak_history(session, pak.id):
                    raise PakCannotBeDeletedError

                oauth_client_id = pak.oauth_client_id
                encrypted_access_key = pak.encrypted_access_key

                try:
                    async with session.begin_nested():
                        try:
                            await self._oauth_clients.delete_client(oauth_client_id)
                            oauth_client_deleted = True

                        except OAuthClientNotFoundError:
                            pass

                        await AuditService.from_session(session).record(
                            actor=_audit_actor(actor),
                            action="pak.deleted",
                            entity=_audit_entity(pak),
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

                    await self._restore_deleted_oauth_client(
                        pak_id=pak_id,
                        oauth_client_id=oauth_client_id,
                        encrypted_access_key=encrypted_access_key,
                    )

                    oauth_client_deleted = False

                    raise PakDeletionSynchronizationError from exc

        except Exception as exc:
            if not oauth_client_deleted or oauth_client_id is None or encrypted_access_key is None:
                raise

            await self._restore_deleted_oauth_client(
                pak_id=pak_id,
                oauth_client_id=oauth_client_id,
                encrypted_access_key=encrypted_access_key,
            )

            logger.bind(
                event="pak.deletion_synchronization_failed",
                pak_id=str(pak_id),
                oauth_client_id=oauth_client_id,
                error_type=type(exc).__name__,
            ).opt(exception=exc).critical("Local PAK deletion failed after OAuth client deletion")

            raise PakDeletionSynchronizationError from exc

    async def _rollback_pak_creation(
        self,
        *,
        pak_id: UUID,
        oauth_client_id: str,
    ) -> None:
        try:
            await self._oauth_clients.delete_client(oauth_client_id)

        except Exception as exc:
            logger.bind(
                event="pak.provisioning_rollback_failed",
                rollback_target="oauth_client",
                pak_id=str(pak_id),
                oauth_client_id=oauth_client_id,
                error_type=type(exc).__name__,
            ).opt(exception=exc).error("Could not roll back PAK OAuth client")

    async def _restore_deleted_oauth_client(
        self,
        *,
        pak_id: UUID,
        oauth_client_id: str,
        encrypted_access_key: str,
    ) -> None:
        try:
            await self._oauth_clients.create_client(
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
            if self._access_key_encryption_key is not None
            else None
        )

        return PakAccessKeyCipher(key)
