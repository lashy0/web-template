from collections.abc import Callable
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import Identity, IdentityManager
from app.auth.exceptions import ForbiddenError, IdentityNotFoundError
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.audit.service import AuditService
from app.modules.audit.types import AuditActor, AuditEntity
from app.modules.users.exceptions import UserProvisioningError
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

BOOTSTRAP_ADMIN_USER_ID = uuid5(NAMESPACE_URL, "web-app/bootstrap-administrator/v1")


class UserManagementService:
    """The only coordinator for Kratos identities, local projections, and audit."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: IdentityManager,
    ) -> None:
        self._session_factory = session_factory
        self._identities = identities
        self._known_sync_issues: set[tuple[str, UUID]] = set()

    async def get(self, user_id: UUID) -> User | None:
        async with self._session_factory() as session:
            return await UserRepository(session).get_by_id(user_id)

    async def list(self, **filters: object) -> tuple[list[User], int]:
        async with self._session_factory() as session:
            return await UserRepository(session).search(**filters)  # type: ignore[arg-type]

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
            login=login, password=password, active=False, user_id=user_id
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

            identity = await self._identities.set_active(identity.id, active=True)

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

            await self._rollback_user_creation(user_id=user_id, identity_id=identity.id)

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
            user = await repository.get_by_id(user_id)

            if user is None:
                raise RuntimeError("Local user disappeared during provisioning")

            user = await repository.update_identity_projection(
                user,
                login=identity.login,
                state="active",
                synced_at=datetime.now(UTC),
            )

            await self._record_user_created(session=session, actor=actor, user=user, active=active)

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
            entity=self._audit_entity(user),
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

    async def bootstrap_first_administrator(
        self, *, name: str, login: str, password_loader: Callable[[], str | None]
    ) -> User | None:
        """Provision or resume the one backend-owned bootstrap administrator."""
        async with self._session_factory() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext('bootstrap-administrator'))")
            )

            repository = UserRepository(session)
            user = await repository.get_by_id(BOOTSTRAP_ADMIN_USER_ID)

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
                    entity=self._audit_entity(user),
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
                    entity=self._audit_entity(user),
                    new_data={
                        "name": user.name,
                        "login": identity.login,
                        "auth_state": "active",
                    },
                )

            return user

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
        login: str | None,
        name: str | None,
        role: Role | None,
    ) -> User:
        async with self._session_factory() as session:
            user = await self._required_user(UserRepository(session), user_id)
            self._ensure_not_archived(user)

        identity: Identity | None = None
        if login is not None and login != user.identity_login:
            identity = await self._identities.update_login(user.identity_id, login=login)

        async with self._session_factory() as session, session.begin():
            await self._lock_admins(session)
            repository = UserRepository(session)

            user = await self._required_user(repository, user_id)
            self._ensure_not_archived(user)

            old_values = {"name": user.name, "role": user.role.value, "login": user.identity_login}

            if role is not None and user.id == actor.user_id and role != Role.ADMINISTRATOR:
                raise ForbiddenError("Cannot remove your own administrator role")

            if role is not None and user.role == Role.ADMINISTRATOR and role != Role.ADMINISTRATOR:
                await self._ensure_not_last_active_admin(repository, user)

            if name is not None and name != user.name:
                await repository.update_name(user, name=name)

            if role is not None and role != user.role:
                await repository.update_role(user, role=role)

            if identity is not None:
                user = await repository.update_identity_projection(
                    user,
                    login=identity.login,
                    state="active" if identity.active else "inactive",
                    synced_at=datetime.now(UTC),
                )

            new_values = {"name": user.name, "role": user.role.value, "login": user.identity_login}
            new_data = {key: value for key, value in new_values.items() if value != old_values[key]}

            if new_data:
                old_data = {key: old_values[key] for key in new_data}

                await AuditService.from_session(session).record(
                    actor=AuditActor.user(
                        actor.user_id,
                        name=actor.name,
                        login=actor.login,
                    ),
                    action="user.updated",
                    entity=self._audit_entity(user),
                    old_data=old_data,
                    new_data=new_data,
                )

            return user

    async def set_password(
        self,
        *,
        actor: CurrentPrincipal,
        user_id: UUID,
        password: str,
    ) -> None:
        async with self._session_factory() as session:
            user = await self._required_user(
                UserRepository(session),
                user_id,
            )

            self._ensure_not_archived(user)

        await self._identities.set_password(
            user.identity_id,
            password=password,
        )

        await self._identities.revoke_all_sessions(
            user.identity_id,
        )

        async with self._session_factory() as session, session.begin():
            user = await self._required_user(
                UserRepository(session),
                user_id,
            )

            await AuditService.from_session(session).record(
                actor=AuditActor.user(
                    actor.user_id,
                    name=actor.name,
                    login=actor.login,
                ),
                action="user.password_changed",
                entity=self._audit_entity(user),
                new_data={
                    "name": user.name,
                    "login": user.identity_login,
                },
            )

    async def set_active(self, *, actor: CurrentPrincipal, user_id: UUID, active: bool) -> User:
        async with self._session_factory() as session, session.begin():
            await self._lock_admins(session)

            user = await self._required_user(UserRepository(session), user_id)
            self._ensure_not_archived(user)

            old_active = user.auth_state == "active"

            if old_active == active:
                return user

            if not active:
                if user.id == actor.user_id:
                    raise ForbiddenError("Cannot deactivate yourself")

                if user.role == Role.ADMINISTRATOR:
                    await self._ensure_not_last_active_admin(UserRepository(session), user)

        identity = await self._identities.set_active(user.identity_id, active=active)

        async with self._session_factory() as session, session.begin():
            user = await self._required_user(UserRepository(session), user_id)
            user = await UserRepository(session).update_identity_projection(
                user,
                login=identity.login,
                state="active" if active else "inactive",
                synced_at=datetime.now(UTC),
            )

            await AuditService.from_session(session).record(
                actor=AuditActor.user(
                    actor.user_id,
                    name=actor.name,
                    login=actor.login,
                ),
                action="user.active_changed",
                entity=self._audit_entity(user),
                old_data={"active": old_active},
                new_data={"active": active},
            )

        if not active:
            await self._identities.revoke_all_sessions(user.identity_id)

        return user

    async def set_archived(self, *, actor: CurrentPrincipal, user_id: UUID, archived: bool) -> User:
        if not archived:
            async with self._session_factory() as session, session.begin():
                repository = UserRepository(session)
                user = await self._required_user(repository, user_id)

                if user.archived_at is None:
                    return user

                user = await repository.update_archived(user, archived_at=None)

                await AuditService.from_session(session).record(
                    actor=AuditActor.user(
                        actor.user_id,
                        name=actor.name,
                        login=actor.login,
                    ),
                    action="user.restored",
                    entity=self._audit_entity(user),
                    new_data={"name": user.name, "login": user.identity_login},
                )

                return user

        async with self._session_factory() as session, session.begin():
            await self._lock_admins(session)

            repository = UserRepository(session)
            user = await self._required_user(repository, user_id)

            if user.archived_at is not None:
                return user

            if user.id == actor.user_id:
                raise ForbiddenError("Cannot archive yourself")

            if user.role == Role.ADMINISTRATOR:
                await self._ensure_not_last_active_admin(repository, user)

        identity = await self._identities.set_active(user.identity_id, active=False)
        archived_at = datetime.now(UTC)

        async with self._session_factory() as session, session.begin():
            repository = UserRepository(session)

            user = await self._required_user(repository, user_id)
            user = await repository.update_identity_projection(
                user,
                login=identity.login,
                state="inactive",
                synced_at=archived_at,
            )

            user = await repository.update_archived(user, archived_at=archived_at)
            await AuditService.from_session(session).record(
                actor=AuditActor.user(
                    actor.user_id,
                    name=actor.name,
                    login=actor.login,
                ),
                action="user.archived",
                entity=self._audit_entity(user),
                new_data={"name": user.name, "login": user.identity_login},
            )

        await self._identities.revoke_all_sessions(user.identity_id)

        return user

    async def delete(self, *, actor: CurrentPrincipal, user_id: UUID) -> None:
        async with self._session_factory() as session, session.begin():
            await self._lock_admins(session)

            repository = UserRepository(session)
            user = await self._required_user(repository, user_id)

            if user.id == actor.user_id:
                raise ForbiddenError("Cannot delete yourself")

            if user.role == Role.ADMINISTRATOR:
                await self._ensure_not_last_active_admin(repository, user)
            identity_id = user.identity_id

        await self._identities.delete_identity(identity_id)

        async with self._session_factory() as session, session.begin():
            repository = UserRepository(session)
            user = await self._required_user(repository, user_id)

            await AuditService.from_session(session).record(
                actor=AuditActor.user(
                    actor.user_id,
                    name=actor.name,
                    login=actor.login,
                ),
                action="user.deleted",
                entity=self._audit_entity(user),
                old_data={"name": user.name, "role": user.role.value, "login": user.identity_login},
            )

            await repository.delete(user)

    async def reconcile(self) -> None:
        """Refresh local projections and report Kratos/PostgreSQL mismatches once per process."""
        identities = {
            item.id: item for item in await self._identities.list_identities(page_size=500)
        }
        current_sync_issues: set[tuple[str, UUID]] = set()

        async with self._session_factory() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext('kratos-reconciler'))")
            )

            repository = UserRepository(session)

            for user in await repository.list_all():
                identity = identities.pop(user.identity_id, None)

                if identity is None:
                    issue = ("db_user_without_kratos_identity", user.id)
                    current_sync_issues.add(issue)

                    if issue not in self._known_sync_issues:
                        logger.bind(
                            event="identity.sync_mismatch_detected",
                            mismatch="db_user_without_kratos_identity",
                            user_id=str(user.id),
                            identity_id=str(user.identity_id),
                        ).error("Local user has no Kratos identity")

                    if user.auth_state != "inactive":
                        await repository.update_identity_projection(
                            user,
                            login=user.identity_login,
                            state="inactive",
                            synced_at=datetime.now(UTC),
                        )
                    continue

                state = "active" if identity.active else "inactive"

                if (user.auth_state, user.identity_login) != (state, identity.login):
                    await repository.update_identity_projection(
                        user, login=identity.login, state=state, synced_at=datetime.now(UTC)
                    )

                    await AuditService.from_session(session).record(
                        actor=AuditActor.system(),
                        action="user.reconciled",
                        entity=self._audit_entity(user),
                        new_data={"name": user.name, "auth_state": state, "login": identity.login},
                    )

            for identity in identities.values():
                issue = ("kratos_identity_without_db_user", identity.id)
                current_sync_issues.add(issue)

                if issue not in self._known_sync_issues:
                    logger.bind(
                        event="identity.sync_mismatch_detected",
                        mismatch="kratos_identity_without_db_user",
                        identity_id=str(identity.id),
                    ).error("Kratos identity has no local user")

        self._known_sync_issues = current_sync_issues

    async def _required_user(self, repository: UserRepository, user_id: UUID) -> User:
        user = await repository.get_by_id(user_id)

        if user is None:
            raise IdentityNotFoundError

        return user

    @staticmethod
    def _audit_entity(user: User) -> AuditEntity:
        return AuditEntity.user(user.id, name=user.name, login=user.identity_login)

    @staticmethod
    def _ensure_not_archived(user: User) -> None:
        if user.archived_at is not None:
            raise ForbiddenError("Cannot modify an archived user")

    async def _bootstrap_identity(
        self, *, login: str, password_loader: Callable[[], str | None]
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

    async def _lock_admins(self, session: AsyncSession) -> None:
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext('active-administrators'))")
        )

    async def _ensure_not_last_active_admin(self, repository: UserRepository, user: User) -> None:
        admins, _ = await repository.search(
            q=None,
            role=Role.ADMINISTRATOR,
            auth_state="active",
            archived=False,
            page=1,
            page_size=2,
            sort="name",
            order="asc",
        )
        active_administrator_ids: set[UUID] = set()

        for administrator in admins:
            identity = await self._identities.get_identity(administrator.identity_id)
            if identity.active:
                active_administrator_ids.add(administrator.id)

        if active_administrator_ids == {user.id}:
            raise ForbiddenError("Cannot change the last active administrator")
