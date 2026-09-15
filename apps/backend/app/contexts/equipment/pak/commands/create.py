from uuid import uuid4

from loguru import logger
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal

from ..audit import audit_actor, audit_entity
from ..contracts import PakOAuthClientPort
from ..crypto import PakAccessKeyCipher
from ..exceptions import PakAlreadyExistsError, PakProvisioningError
from ..model import PakDevice, PakDeviceKind
from ..repository import PakRepository


class CreatePak:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        oauth: PakOAuthClientPort,
        access_key_encryption_key: SecretStr | None,
    ) -> None:
        self._session_factory = session_factory
        self._oauth = oauth
        self._access_key_encryption_key = access_key_encryption_key

    async def execute(
        self, *, actor: CurrentPrincipal, code: str, kind: PakDeviceKind, active: bool
    ) -> tuple[PakDevice, str]:
        pak_id = uuid4()
        oauth_client_id = f"pak-{pak_id}"
        async with self._session_factory() as session:
            if await PakRepository(session).get_by_code(code) is not None:
                raise PakAlreadyExistsError

        credentials = await self._oauth.create_client(client_id=oauth_client_id)
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
                await TransactionalAuditWriter.from_session(session).record(
                    actor=audit_actor(actor),
                    action="pak.created",
                    entity=audit_entity(pak),
                    new_data={
                        "pak_id": str(pak.id),
                        "code": pak.code,
                        "oauth_client_id": pak.oauth_client_id,
                        "active": pak.is_active,
                    },
                )
                return pak, credentials.client_secret
        except IntegrityError as exc:
            await self._compensate(pak_id=pak_id, oauth_client_id=credentials.client.client_id)
            raise PakAlreadyExistsError from exc
        except Exception as exc:
            logger.bind(
                event="pak.provisioning_failed",
                pak_id=str(pak_id),
                oauth_client_id=oauth_client_id,
                error_type=type(exc).__name__,
            ).opt(exception=exc).error("PAK provisioning failed")
            await self._compensate(pak_id=pak_id, oauth_client_id=credentials.client.client_id)
            raise PakProvisioningError from exc

    async def _compensate(self, *, pak_id: object, oauth_client_id: str) -> None:
        try:
            await self._oauth.delete_client(oauth_client_id)
        except Exception as exc:
            logger.bind(
                event="pak.provisioning_rollback_failed",
                pak_id=str(pak_id),
                oauth_client_id=oauth_client_id,
                error_type=type(exc).__name__,
            ).opt(exception=exc).error("Could not roll back PAK OAuth client")

    def _cipher(self) -> PakAccessKeyCipher:
        key = (
            self._access_key_encryption_key.get_secret_value()
            if self._access_key_encryption_key
            else None
        )
        return PakAccessKeyCipher(key)
