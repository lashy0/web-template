from datetime import UTC, datetime
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import CurrentPrincipal, Role

from ..audit import audit_actor, audit_entity
from ..contracts import UserIdentityProviderPort
from ..exceptions import UserProvisioningError
from ..model import User
from ..queries import required_user
from ..repository import UserRepository


class CreateUser:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: UserIdentityProviderPort,
    ) -> None:
        self._session_factory = session_factory
        self._identities = identities

    async def execute(
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
        # Preserve the baseline safety ordering: an uncommitted local failure never grants access.
        identity = await self._identities.create_identity(
            login=login, password=password, active=False, user_id=user_id
        )
        try:
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
                if not active:
                    await self._record_created(session, actor, user, active=False)
            if not active:
                return user
            async with self._session_factory() as session, session.begin():
                repository = UserRepository(session)
                user = await required_user(repository, user_id)
                identity = await self._identities.set_active(identity.id, active=True)
                user = await repository.update_identity_projection(
                    user, login=identity.login, state="active", synced_at=datetime.now(UTC)
                )
                await self._record_created(session, actor, user, active=True)
                return user
        except Exception as exc:
            logger.bind(
                event="user.provisioning_failed",
                user_id=str(user_id),
                identity_id=str(identity.id),
                error_type=type(exc).__name__,
            ).opt(exception=exc).error("User provisioning failed")
            await self._rollback(user_id=user_id, identity_id=identity.id)
            raise UserProvisioningError from exc

    async def _record_created(
        self, session: AsyncSession, actor: CurrentPrincipal | None, user: User, *, active: bool
    ) -> None:
        await TransactionalAuditWriter.from_session(session).record(
            actor=audit_actor(actor),
            action="user.created",
            entity=audit_entity(user),
            new_data={
                "name": user.name,
                "role": user.role.value,
                "login": user.identity_login,
                "active": active,
            },
        )

    async def _rollback(self, *, user_id: UUID, identity_id: UUID) -> None:
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
