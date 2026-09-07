from datetime import UTC, datetime
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import Identity, IdentityManager
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.audit.service import AuditService
from app.modules.audit.types import AuditActor

from ..exceptions import UserProvisioningError
from ..models import User
from ..repository import UserRepository
from .audit import _audit_entity


class UserProvisioningService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: IdentityManager,
    ) -> None:
        self._session_factory = session_factory
        self._identities = identities

    async def create(
        self,
        *,
        actor: CurrentPrincipal | None,
        name: str,
        role: Role,
        login: str,
        password: str,
        active: bool,
    ) -> User:
        user_id = uuid4()
        # Kratos is created inactive first so a failed local transaction cannot grant access.
        identity = await self._identities.create_identity(
            login=login,
            password=password,
            active=False,
            user_id=user_id,
        )

        try:
            user = await self._create_local_user(
                actor=actor,
                user_id=user_id,
                identity=identity,
                name=name,
                role=role,
                active=active,
                record_created=not active,
            )

            if not active:
                return user

            return await self._complete_active_user_creation(
                actor=actor,
                user_id=user_id,
                identity=identity,
                active=active,
            )

        except Exception as exc:
            logger.bind(
                event="user.provisioning_failed",
                user_id=str(user_id),
                identity_id=str(identity.id),
                error_type=type(exc).__name__,
            ).opt(exception=exc).error("User provisioning failed")

            await self._rollback_user_creation(
                user_id=user_id,
                identity_id=identity.id,
            )

            raise UserProvisioningError from exc

    async def _create_local_user(
        self,
        *,
        actor: CurrentPrincipal | None,
        user_id: UUID,
        identity: Identity,
        name: str,
        role: Role,
        active: bool,
        record_created: bool,
    ) -> User:
        async with self._session_factory() as session, session.begin():
            user = await UserRepository(session).create(
                user_id=user_id,
                identity_id=identity.id,
                name=name,
                role=role,
                identity_login=identity.login,
                auth_state="inactive",
                synced_at=datetime.now(UTC),
            )

            if record_created:
                await self._record_user_created(
                    session=session,
                    actor=actor,
                    user=user,
                    active=active,
                )

            return user

    async def _complete_active_user_creation(
        self,
        *,
        actor: CurrentPrincipal | None,
        user_id: UUID,
        identity: Identity,
        active: bool,
    ) -> User:
        async with self._session_factory() as session, session.begin():
            repository = UserRepository(session)
            user = await repository.get_by_id(user_id, for_update=True)

            if user is None:
                raise RuntimeError("Local user disappeared during provisioning")

            identity = await self._identities.set_active(identity.id, active=True)

            user = await repository.update_identity_projection(
                user,
                login=identity.login,
                state="active",
                synced_at=datetime.now(UTC),
            )

            await self._record_user_created(
                session=session,
                actor=actor,
                user=user,
                active=active,
            )

            return user

    async def _record_user_created(
        self,
        *,
        session: AsyncSession,
        actor: CurrentPrincipal | None,
        user: User,
        active: bool,
    ) -> None:
        audit_actor = (
            AuditActor.user(actor.user_id, name=actor.name, login=actor.login)
            if actor
            else AuditActor.system()
        )

        await AuditService.from_session(session).record(
            actor=audit_actor,
            action="user.created",
            entity=_audit_entity(user),
            new_data={
                "name": user.name,
                "role": user.role.value,
                "login": user.identity_login,
                "active": active,
            },
        )

    async def _rollback_user_creation(self, *, user_id: UUID, identity_id: UUID) -> None:
        try:
            await self._identities.delete_identity(identity_id)

        except Exception as exc:
            logger.bind(
                event="user.provisioning_rollback_failed",
                rollback_target="kratos_identity",
                user_id=str(user_id),
                identity_id=str(identity_id),
                error_type=type(exc).__name__,
            ).opt(exception=exc).error("Could not roll back Kratos identity")

        try:
            async with self._session_factory() as session, session.begin():
                await UserRepository(session).delete_if_exists(user_id)

        except Exception as exc:
            logger.bind(
                event="user.provisioning_rollback_failed",
                rollback_target="db_user",
                user_id=str(user_id),
                identity_id=str(identity_id),
                error_type=type(exc).__name__,
            ).opt(exception=exc).error("Could not roll back local user")
