"""Changes made through the API: their audit entries and realtime events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.lib.realtime import announce_after_commit

if TYPE_CHECKING:
    from litestar import Request

    from app.domain.audit.services import AuditLogService
    from app.lib.audit import Actor, AuditTarget
    from app.lib.realtime import Realtime, RealtimeEvent
    from app.lib.uow import UnitOfWork


class ChangeRecorder:
    """Record changes with the actor supplied by the request's provider.

    A recorded change gets an audit entry in the request's transaction and an
    event announced once it commits. A handler that requests the recorder
    requests the unit of work with it, so its change commits.
    """

    __slots__ = ("_actor", "_audit", "_realtime", "_request", "_uow")

    def __init__(
        self,
        request: Request[Any, Any, Any],
        audit: AuditLogService,
        uow: UnitOfWork,
        realtime: Realtime,
        actor: Actor,
    ) -> None:
        self._request = request
        self._audit = audit
        self._uow = uow
        self._realtime = realtime
        self._actor = actor

    async def record(
        self,
        action: str,
        target: AuditTarget,
        *,
        event: RealtimeEvent,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Write the audit entry of ``action`` on ``target`` and announce ``event`` after the commit."""
        await self._audit.log_action(
            action=action,
            actor_id=self._actor.id,
            actor_login=self._actor.login,
            actor_name=self._actor.name,
            target=target,
            details=details,
            request=self._request,
        )
        self.announce(event)

    def announce(self, *events: RealtimeEvent) -> None:
        """Announce events after the commit, for changes the audit log does not record."""
        for event in events:
            announce_after_commit(self._uow, self._realtime, event)


__all__ = ("ChangeRecorder",)
