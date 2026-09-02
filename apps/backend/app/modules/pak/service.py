from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from loguru import logger
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import (
    MachineTokenIssuer,
    OAuthAccessToken,
    OAuthClientManager,
    TokenIntrospector,
)
from app.auth.exceptions import ForbiddenError, InvalidMachineCredentialsError
from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService
from app.modules.audit.types import AuditActor, AuditEntity
from app.modules.defects.repository import DefectGroupRepository
from app.modules.pak.crypto import PakAccessKeyCipher
from app.modules.pak.exceptions import (
    InvalidMachineAccessTokenError,
    PakAlreadyExistsError,
    PakCannotBeDeletedError,
    PakNotFoundError,
    PakProvisioningError,
    PakTestConfigurationError,
    PakTestNotFoundError,
)
from app.modules.pak.models import PakDevice, PakDeviceKind, PakTest
from app.modules.pak.repository import PakRepository, PakTestRepository
from app.modules.verification.repository import VerificationSessionRepository

PAK_OAUTH_SCOPES = ("pak:api",)
PAK_LAST_SEEN_UPDATE_INTERVAL = timedelta(seconds=15)


class PakManagementService:
    """Coordinates OAuth clients, encrypted PAK keys, local state, and audit."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        oauth_clients: OAuthClientManager,
        token_introspector: TokenIntrospector,
        token_issuer: MachineTokenIssuer,
        access_key_encryption_key: SecretStr | None,
    ) -> None:
        self._session_factory = session_factory
        self._oauth_clients = oauth_clients
        self._token_introspector = token_introspector
        self._token_issuer = token_issuer
        self._access_key_encryption_key = access_key_encryption_key

    async def get(self, pak_id: UUID) -> PakDevice | None:
        async with self._session_factory() as session:
            return await PakRepository(session).get_by_id(pak_id)

    async def list(self, **filters: object) -> tuple[list[PakDevice], int]:
        async with self._session_factory() as session:
            return await PakRepository(session).search(**filters)  # type: ignore[arg-type]

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

        cipher = self._cipher()
        credentials = await self._oauth_clients.create_client(
            client_id=oauth_client_id,
            scopes=PAK_OAUTH_SCOPES,
        )
        encrypted_access_key = cipher.encrypt(credentials.client_secret)

        try:
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
                    actor=self._audit_actor(actor),
                    action="pak.created",
                    entity=self._audit_entity(pak),
                    new_data={
                        "pak_id": str(pak.id),
                        "code": pak.code,
                        "oauth_client_id": pak.oauth_client_id,
                        "active": pak.is_active,
                    },
                )

                return pak, credentials.client_secret

        except IntegrityError as exc:
            await self._rollback_pak_creation(pak_id=pak_id, oauth_client_id=oauth_client_id)

            raise PakAlreadyExistsError from exc

        except Exception as exc:
            logger.bind(
                event="pak.provisioning_failed",
                pak_id=str(pak_id),
                oauth_client_id=oauth_client_id,
                error_type=type(exc).__name__,
            ).opt(exception=exc).error("PAK provisioning failed")

            await self._rollback_pak_creation(pak_id=pak_id, oauth_client_id=oauth_client_id)

            raise PakProvisioningError from exc

    async def get_access_key(self, *, actor: CurrentPrincipal, pak_id: UUID) -> str:
        async with self._session_factory() as session, session.begin():
            pak = await self._required_pak(PakRepository(session), pak_id)
            access_key = self._cipher().decrypt(pak.encrypted_access_key)

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="pak.access_key_viewed",
                entity=self._audit_entity(pak),
                new_data={
                    "pak_id": str(pak.id),
                    "code": pak.code,
                    "oauth_client_id": pak.oauth_client_id,
                },
            )

            return access_key

    async def rotate_access_key(self, *, actor: CurrentPrincipal, pak_id: UUID) -> str:
        async with self._session_factory() as session:
            pak = await self._required_pak(PakRepository(session), pak_id)
            self._ensure_not_archived(pak)
            oauth_client_id = pak.oauth_client_id

        cipher = self._cipher()
        credentials = await self._oauth_clients.rotate_client_credentials(oauth_client_id)

        if credentials.client.client_id != oauth_client_id:
            raise PakProvisioningError("OAuth provider changed the PAK client ID during rotation")

        encrypted_access_key = cipher.encrypt(credentials.client_secret)

        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)
            pak = await self._required_pak(repository, pak_id)
            self._ensure_not_archived(pak)

            if pak.oauth_client_id != oauth_client_id:
                raise PakProvisioningError("PAK OAuth client changed during access-key rotation")

            pak = await repository.update_access_key(pak, encrypted_access_key=encrypted_access_key)

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="pak.access_key_rotated",
                entity=self._audit_entity(pak),
                new_data={
                    "pak_id": str(pak.id),
                    "code": pak.code,
                    "oauth_client_id": pak.oauth_client_id,
                },
            )

        return str(credentials.client_secret)

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
        code: str | None,
        kind: PakDeviceKind | None,
    ) -> PakDevice:
        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)
            pak = await self._required_pak(repository, pak_id)
            self._ensure_not_archived(pak)
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
            new_data = {key: value for key, value in new_values.items() if value != old_values[key]}

            if new_data:
                await AuditService.from_session(session).record(
                    actor=self._audit_actor(actor),
                    action="pak.updated",
                    entity=self._audit_entity(pak),
                    old_data={key: old_values[key] for key in new_data},
                    new_data=new_data,
                )

            return pak

    async def set_active(self, *, actor: CurrentPrincipal, pak_id: UUID, active: bool) -> PakDevice:
        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)
            pak = await self._required_pak(repository, pak_id)
            self._ensure_not_archived(pak)
            old_active = pak.is_active

            if old_active == active:
                return pak

            pak = await repository.update_active(pak, active=active)

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="pak.active_changed",
                entity=self._audit_entity(pak),
                old_data={"active": old_active},
                new_data={"active": active},
            )

            return pak

    async def set_archived(
        self, *, actor: CurrentPrincipal, pak_id: UUID, archived: bool
    ) -> PakDevice:
        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)
            pak = await self._required_pak(repository, pak_id)

            if not archived:
                if pak.archived_at is None:
                    return pak

                pak = await repository.update_archived(pak, archived_at=None)
                action = "pak.restored"
                old_data: dict[str, object] | None = None
                new_data: dict[str, object] = {"active": pak.is_active}
            else:
                if pak.archived_at is not None:
                    return pak

                old_active = pak.is_active

                if pak.is_active:
                    pak = await repository.update_active(pak, active=False)

                archived_at = datetime.now(UTC)
                pak = await repository.update_archived(pak, archived_at=archived_at)
                action = "pak.archived"
                old_data = {"active": old_active}
                new_data = {"active": False, "archived_at": archived_at.isoformat()}

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action=action,
                entity=self._audit_entity(pak),
                old_data=old_data,
                new_data=new_data,
            )

            return pak

    async def delete(self, *, actor: CurrentPrincipal, pak_id: UUID) -> None:
        async with self._session_factory() as session:
            pak = await self._required_pak(PakRepository(session), pak_id)

            has_verification_history = await VerificationSessionRepository(
                session
            ).exists_by_pak_id(pak.id)

            if has_verification_history:
                raise PakCannotBeDeletedError

            oauth_client_id = pak.oauth_client_id

        await self._oauth_clients.delete_client(oauth_client_id)

        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)
            pak = await self._required_pak(repository, pak_id)

            await AuditService.from_session(session).record(
                actor=self._audit_actor(actor),
                action="pak.deleted",
                entity=self._audit_entity(pak),
                old_data={
                    "pak_id": str(pak.id),
                    "code": pak.code,
                    "oauth_client_id": pak.oauth_client_id,
                },
            )

            await repository.delete(pak)

    async def issue_machine_access_token(
        self,
        *,
        client_id: str,
        access_key: str,
    ) -> OAuthAccessToken:
        token = await self._token_issuer.issue_client_credentials_token(
            client_id=client_id,
            client_secret=access_key,
            scopes=PAK_OAUTH_SCOPES,
        )

        async with self._session_factory() as session:
            pak = await PakRepository(session).get_by_oauth_client_id(client_id)

        if pak is None:
            raise InvalidMachineCredentialsError

        if not pak.is_active or pak.archived_at is not None:
            raise ForbiddenError(
                "PAK is inactive or archived"
            )

        return token

    async def authorize_machine_access_token(self, access_token: str) -> PakDevice:
        """Authorize a PAK token against live local active/archive state."""
        introspection = await self._token_introspector.introspect_access_token(
            access_token, required_scopes=PAK_OAUTH_SCOPES
        )

        if not introspection.active or not introspection.client_id:
            raise InvalidMachineAccessTokenError

        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)

            pak = await repository.get_by_oauth_client_id(introspection.client_id)

            if pak is None:
                raise InvalidMachineAccessTokenError

            if not pak.is_active or pak.archived_at is not None:
                raise ForbiddenError(
                    "PAK is inactive or archived"
                )

            now = datetime.now(UTC)

            if (
                pak.last_seen_at is None
                or now - pak.last_seen_at
                >= PAK_LAST_SEEN_UPDATE_INTERVAL
            ):
                pak = await repository.update_last_seen(pak, last_seen_at=now)

            return pak

    async def _rollback_pak_creation(self, *, pak_id: UUID, oauth_client_id: str) -> None:
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

    def _cipher(self) -> PakAccessKeyCipher:
        key = (
            self._access_key_encryption_key.get_secret_value()
            if self._access_key_encryption_key is not None
            else None
        )

        return PakAccessKeyCipher(key)

    @staticmethod
    async def _required_pak(repository: PakRepository, pak_id: UUID) -> PakDevice:
        pak = await repository.get_by_id(pak_id)

        if pak is None:
            raise PakNotFoundError

        return pak

    @staticmethod
    def _audit_actor(actor: CurrentPrincipal) -> AuditActor:
        return AuditActor.user(actor.user_id, name=actor.name, login=actor.login)

    @staticmethod
    def _audit_entity(pak: PakDevice) -> AuditEntity:
        return AuditEntity(
            type="pak", id=str(pak.id), display_name=pak.code, identifier=pak.oauth_client_id
        )

    @staticmethod
    def _ensure_not_archived(pak: PakDevice) -> None:
        if pak.archived_at is not None:
            raise ForbiddenError("Cannot modify an archived PAK")


class PakTestCatalogService:
    """Tracks tests reported by PAK devices."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get(self, test_id: UUID) -> PakTest | None:
        async with self._session_factory() as session:
            return await PakTestRepository(session).get_by_id(test_id)

    async def get_by_test_name(self, test_name: str) -> PakTest | None:
        async with self._session_factory() as session:
            return await PakTestRepository(session).get_by_test_name(test_name)

    async def list(self, **filters: object) -> tuple[list[PakTest], int]:
        async with self._session_factory() as session:
            return await PakTestRepository(session).search(**filters) # type: ignore[arg-type]

    async def observe(
        self,
        *,
        pak: PakDevice,
        test_name: str,
        test_label: str,
        defect_group_code: str,
        seen_at: datetime | None = None,
    ) -> PakTest:
        observed_at = seen_at or datetime.now(UTC)

        async with self._session_factory() as session, session.begin():
            return await self.observe_in_session(
                session,
                pak=pak,
                test_name=test_name,
                test_label=test_label,
                defect_group_code=defect_group_code,
                seen_at=observed_at,
            )

    async def observe_in_session(
        self,
        session: AsyncSession,
        *,
        pak: PakDevice,
        test_name: str,
        test_label: str,
        defect_group_code: str,
        seen_at: datetime,
    ) -> PakTest:
        group_repository = DefectGroupRepository(session)
        test_repository = PakTestRepository(session)

        group = await group_repository.get_by_code(defect_group_code)

        if group is None:
            self._log_configuration_error(
                pak=pak,
                test_name=test_name,
                defect_group_code=defect_group_code,
                reason="unknown_defect_group",
            )

            raise PakTestConfigurationError(
                "PAK test references an unknown defect group",
                details={
                    "pak_id": str(pak.id),
                    "pak_code": pak.code,
                    "test_name": test_name,
                    "defect_group_code": defect_group_code,
                },
            )

        if group.archived_at is not None:
            self._log_configuration_error(
                pak=pak,
                test_name=test_name,
                defect_group_code=defect_group_code,
                reason="archived_defect_group",
            )

            raise PakTestConfigurationError(
                "PAK test references an archived defect group",
                details={
                    "pak_id": str(pak.id),
                    "pak_code": pak.code,
                    "test_name": test_name,
                    "defect_group_code": defect_group_code,
                },
            )

        test = await test_repository.get_by_test_name(test_name)

        if test is None:
            test = await test_repository.create(
                test_name=test_name,
                test_label=test_label,
                defect_group_id=group.id,
                last_seen_at=seen_at,
            )

            await AuditService.from_session(session).record(
                actor=self._audit_actor(pak),
                action="pak_test.created",
                entity=self._audit_entity(test),
                new_data={
                    "test_name": test.test_name,
                    "test_label": test.test_label,
                    "defect_group_id": str(
                        test.defect_group_id
                    ),
                    "defect_group_code": group.code,
                },
            )

            return test

        old_data: dict[str, object] = {}
        new_data: dict[str, object] = {}

        if test.test_label != test_label:
            old_data["test_label"] = test.test_label
            new_data["test_label"] = test_label

        if test.defect_group_id != group.id:
            old_data["defect_group_id"] = str(
                test.defect_group_id
            )
            new_data["defect_group_id"] = str(
                group.id
            )

            old_data["defect_group_code"] = (
                await self._get_group_code(
                    group_repository,
                    test.defect_group_id,
                )
            )
            new_data["defect_group_code"] = group.code

        test = await test_repository.update_observation(
            test,
            test_label=test_label,
            defect_group_id=group.id,
            last_seen_at=seen_at,
        )

        if new_data:
            await AuditService.from_session(session).record(
                actor=self._audit_actor(pak),
                action="pak_test.updated",
                entity=self._audit_entity(test),
                old_data=old_data,
                new_data=new_data,
            )

        return test

    async def require(self, test_id: UUID) -> PakTest:
        test = await self.get(test_id)

        if test is None:
            raise PakTestNotFoundError

        return test

    @staticmethod
    async def _get_group_code(
        repository: DefectGroupRepository,
        group_id: UUID,
    ) -> str | None:
        group = await repository.get_by_id(group_id)

        if group is None:
            return None

        return group.code

    @staticmethod
    def _audit_actor(pak: PakDevice) -> AuditActor:
        return AuditActor(
            type="pak",
            id=str(pak.id),
            display_name=pak.code,
            identifier=pak.oauth_client_id,
        )

    @staticmethod
    def _audit_entity(test: PakTest) -> AuditEntity:
        return AuditEntity(
            type="pak_test",
            id=str(test.id),
            display_name=test.test_label,
            identifier=test.test_name,
        )

    @staticmethod
    def _log_configuration_error(
        *,
        pak: PakDevice,
        test_name: str,
        defect_group_code: str,
        reason: str,
    ) -> None:
        logger.bind(
            event="pak_test.configuration_error",
            pak_id=str(pak.id),
            pak_code=pak.code,
            test_name=test_name,
            defect_group_code=defect_group_code,
            reason=reason,
        ).warning(
            "PAK test references an invalid defect group"
        )
