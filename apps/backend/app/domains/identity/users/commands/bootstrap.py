from collections.abc import Callable
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.writer import TransactionalAuditWriter
from app.shared.security import Identity, IdentityNotFoundError, Role

from ..audit import audit_actor, audit_entity
from ..contracts import UserIdentityProviderPort
from ..model import User
from ..repository import UserRepository
from ..rules import BOOTSTRAP_ADMIN_USER_ID_NAMESPACE

BOOTSTRAP_ADMIN_USER_ID = uuid5(NAMESPACE_URL, BOOTSTRAP_ADMIN_USER_ID_NAMESPACE)


class BootstrapFirstAdministrator:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: UserIdentityProviderPort,
    ) -> None:
        self._session_factory, self._identities = session_factory, identities

    async def execute(
        self, *, name: str, login: str, password_loader: Callable[[], str | None]
    ) -> User | None:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext('bootstrap-administrator'))")
            )
            repository = UserRepository(session)
            user = await repository.get_by_id(BOOTSTRAP_ADMIN_USER_ID, for_update=True)
            if user is None and await repository.count() > 0:
                return None
            identity = await self._identity(login=login, password_loader=password_loader)
            if user is None:
                user = await repository.create(
                    user_id=BOOTSTRAP_ADMIN_USER_ID,
                    identity_id=identity.id,
                    name=name,
                    role=Role.ADMINISTRATOR,
                    identity_login=identity.login,
                    auth_state="active" if identity.active else "inactive",
                    synced_at=datetime.now(UTC),
                )
                await TransactionalAuditWriter.from_session(session).record(
                    actor=audit_actor(None),
                    action="user.bootstrap_created",
                    entity=audit_entity(user),
                    new_data={"name": name, "role": Role.ADMINISTRATOR.value, "login": login},
                )
            if user.identity_id != identity.id:
                raise ValueError(
                    "Bootstrap administrator identity does not match its local projection"
                )
            if not identity.active:
                identity = await self._identities.set_active(identity.id, active=True)
            if (user.identity_login, user.auth_state) != (identity.login, "active"):
                user = await repository.update_identity_projection(
                    user, login=identity.login, state="active", synced_at=datetime.now(UTC)
                )
                await TransactionalAuditWriter.from_session(session).record(
                    actor=audit_actor(None),
                    action="user.bootstrap_completed",
                    entity=audit_entity(user),
                    new_data={"name": user.name, "login": identity.login, "auth_state": "active"},
                )
            return user

    async def _identity(self, *, login: str, password_loader: Callable[[], str | None]) -> Identity:
        try:
            identity = await self._identities.get_identity_by_external_id(BOOTSTRAP_ADMIN_USER_ID)
        except IdentityNotFoundError:
            password = password_loader()
            if password is None:
                raise ValueError(
                    "BACKEND_BOOTSTRAP_ADMIN_PASSWORD or BACKEND_BOOTSTRAP_ADMIN_PASSWORD_FILE is required for the first startup"
                ) from None
            identity = await self._identities.create_identity(
                login=login,
                password=password,
                active=False,
                user_id=BOOTSTRAP_ADMIN_USER_ID,
                provisioning_kind="bootstrap",
            )
        provisioning = (identity.metadata or {}).get("provisioning")
        if (
            not isinstance(provisioning, dict)
            or provisioning.get("owner") != "backend"
            or provisioning.get("version") != 1
            or provisioning.get("kind") != "bootstrap"
            or provisioning.get("user_id") != str(BOOTSTRAP_ADMIN_USER_ID)
        ):
            raise ValueError("Bootstrap identity is not owned by this backend")
        if identity.login != login:
            raise ValueError("Bootstrap administrator login does not match its configuration")
        return identity
