from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import IdentityManager
from app.modules.audit.service import AuditService
from app.modules.audit.types import AuditActor

from ..repository import UserRepository
from .audit import _audit_entity


@dataclass
class ReconciliationResult:
    processed: int = 0
    updated: int = 0
    conflicts: int = 0
    mismatches: int = 0


class UserReconciliationService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        identities: IdentityManager,
        *,
        page_size: int = 500,
    ) -> None:
        self._session_factory = session_factory
        self._identities = identities
        self._page_size = page_size
        self._known_sync_issues: set[tuple[str, UUID]] = set()

    async def reconcile(self) -> ReconciliationResult:
        """Apply provider snapshots only to unchanged, currently unlocked users."""
        result = ReconciliationResult()
        current_sync_issues: set[tuple[str, UUID]] = set()

        # Snapshot versions BEFORE provider I/O; release the read transaction first.
        async with self._session_factory() as session:
            snapshots = await UserRepository(session).list_all()

        identities = {
            item.id: item
            for item in await self._identities.list_identities(page_size=self._page_size)
        }

        for snapshot in snapshots:
            identity = identities.pop(snapshot.identity_id, None)
            result.processed += 1

            async with self._session_factory() as session, session.begin():
                repository = UserRepository(session)
                user = await repository.get_for_reconciliation(snapshot.id, snapshot.version)

                if user is None:
                    result.conflicts += 1
                    # A busy user is not evidence that a previously observed issue resolved.
                    issue = ("db_user_without_kratos_identity", snapshot.id)
                    if issue in self._known_sync_issues:
                        current_sync_issues.add(issue)

                    continue

                state = "active" if identity is not None and identity.active else "inactive"
                login = identity.login if identity is not None else user.identity_login

                if (user.auth_state, user.identity_login) != (state, login):
                    applied = await repository.reconcile_projection(
                        user, login=login, state=state, synced_at=datetime.now(UTC)
                    )

                    if not applied:
                        result.conflicts += 1
                        continue

                    await AuditService.from_session(session).record(
                        actor=AuditActor.system(),
                        action="user.reconciled",
                        entity=_audit_entity(user),
                        new_data={
                            "name": user.name,
                            "auth_state": state,
                            "login": login,
                        },
                    )
                    result.updated += 1

            # Report only after the transaction has committed successfully.
            if identity is None:
                issue = ("db_user_without_kratos_identity", snapshot.id)
                current_sync_issues.add(issue)

                if issue not in self._known_sync_issues:
                    logger.bind(
                        event="identity.sync_mismatch_detected",
                        mismatch=issue[0],
                        user_id=str(snapshot.id),
                        identity_id=str(snapshot.identity_id),
                    ).error("Local user has no Kratos identity")

        for identity in identities.values():
            # A user may have been provisioned after our initial local snapshot.
            async with self._session_factory() as session:
                if await UserRepository(session).get_by_identity_id(identity.id) is not None:
                    continue

            issue = ("kratos_identity_without_db_user", identity.id)
            current_sync_issues.add(issue)

            if issue not in self._known_sync_issues:
                logger.bind(
                    event="identity.sync_mismatch_detected",
                    mismatch=issue[0],
                    identity_id=str(identity.id),
                ).error("Kratos identity has no local user")

        self._known_sync_issues = current_sync_issues
        result.mismatches = len(current_sync_issues)

        return result
