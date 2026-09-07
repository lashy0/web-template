from collections.abc import Callable
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import Identity, IdentityManager
from app.auth.exceptions import IdentityNotFoundError
from app.auth.roles import Role
from app.modules.audit.service import AuditService
from app.modules.audit.types import AuditActor

from ..models import User
from ..repository import UserRepository
from .audit import _audit_entity

BOOTSTRAP_ADMIN_USER_ID = uuid5(NAMESPACE_URL, "web-app/bootstrap-administrator/v1")


class UserBootstrapService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: IdentityManager,
    ) -> None:
        self._session_factory = session_factory
        self._identities = identities

    async def bootstrap_first_administrator(
        self,
        *,
        name: str,
        login: str,
        password_loader: Callable[[], str | None],
    ) -> User | None:
        """Provision or resume the one backend-owned bootstrap administrator."""
        async with self._session_factory() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext('bootstrap-administrator'))")
            )

            repository = UserRepository(session)
            user = await repository.get_by_id(BOOTSTRAP_ADMIN_USER_ID, for_update=True)

            if user is None and await repository.count() > 0:
                return None

            identity = await self._bootstrap_identity(login=login, password_loader=password_loader)

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

                await AuditService.from_session(session).record(
                    actor=AuditActor.system(),
                    action="user.bootstrap_created",
                    entity=_audit_entity(user),
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
                    user,
                    login=identity.login,
                    state="active",
                    synced_at=datetime.now(UTC),
                )

                await AuditService.from_session(session).record(
                    actor=AuditActor.system(),
                    action="user.bootstrap_completed",
                    entity=_audit_entity(user),
                    new_data={
                        "name": user.name,
                        "login": identity.login,
                        "auth_state": "active",
                    },
                )

            return user

    async def _bootstrap_identity(
        self,
        *,
        login: str,
        password_loader: Callable[[], str | None],
    ) -> Identity:
        try:
            identity = await self._identities.get_identity_by_external_id(BOOTSTRAP_ADMIN_USER_ID)

        except IdentityNotFoundError:
            password = password_loader()

            if password is None:
                raise ValueError(
                    "BACKEND_BOOTSTRAP_ADMIN_PASSWORD or "
                    "BACKEND_BOOTSTRAP_ADMIN_PASSWORD_FILE is required for the first startup"
                ) from None

            identity = await self._identities.create_identity(
                login=login,
                password=password,
                active=False,
                user_id=BOOTSTRAP_ADMIN_USER_ID,
                provisioning_kind="bootstrap",
            )

        metadata = identity.metadata or {}
        provisioning = metadata.get("provisioning")

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
