"""System domain controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from litestar import Controller, MediaType, Request, get
from litestar.di import NamedDependency
from litestar.response import Response, ServerSentEvent
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import models as m
from app.domain.system import schemas as s
from app.lib.authorization import granted_permissions
from app.lib.openapi import error_responses
from app.lib.realtime import Realtime, event_stream

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.config.settings import AppSettings
    from app.lib.hydra import HydraClient
    from app.lib.kratos import KratosClient

_RECONNECT_DELAY_MS = 2000


class SystemController(Controller):
    """System health and configuration."""

    tags = ["System"]  # noqa: RUF012
    dependencies = {}  # noqa: RUF012

    @get(
        operation_id="SystemHealth",
        name="system:health",
        path="/health",
        summary="Health Check",
        exclude_from_auth=True,
        security=[],  # Public endpoint - no auth required
    )
    async def check_system_health(
        self,
        db_session: NamedDependency[AsyncSession],
        settings: NamedDependency[AppSettings],
        hydra: NamedDependency[HydraClient],
        kratos: NamedDependency[KratosClient],
    ) -> Response[s.SystemHealth]:
        """Check database availability and return application config info.

        Args:
            db_session: The database session.
            settings: Application settings.

        Returns:
            The response object.
        """
        database_status: Literal["online", "offline"]

        try:
            await db_session.execute(text("select 1"))
            database_status = "online"

        # asyncpg reports a refused connection as a plain OSError, not a DBAPI error.
        except (SQLAlchemyError, OSError):
            database_status = "offline"

        kratos_status: Literal["online", "offline"] = "online" if await kratos.is_ready() else "offline"
        hydra_status: Literal["online", "offline"] = "online" if await hydra.is_ready() else "offline"
        healthy = database_status == "online" and kratos_status == "online" and hydra_status == "online"

        return Response(
            content=s.SystemHealth(
                app=settings.name,
                database_status=database_status,
                kratos_status=kratos_status,
                hydra_status=hydra_status,
            ),
            status_code=200 if healthy else 503,
            media_type=MediaType.JSON,
        )

    @get(
        operation_id="SystemVersion",
        name="system:version",
        path="/system/version",
        summary="Release Version",
        exclude_from_auth=True,
        security=[],  # Public endpoint - no auth required
    )
    async def get_system_version(self, settings: NamedDependency[AppSettings]) -> s.SystemVersion:
        """Return the release version of the running backend, ``dev`` outside a release."""
        return s.SystemVersion(version=settings.version)


class EventController(Controller):
    """Realtime events of the signed-in user, as server-sent events."""

    tags = ["Realtime"]  # noqa: RUF012

    @get(
        operation_id="StreamEvents",
        path="/events",
        summary="Event Stream",
        media_type="text/event-stream",
        responses=error_responses(401),
    )
    async def stream_events(
        self,
        request: Request[m.User, Any, Any],
        realtime: NamedDependency[Realtime],
    ) -> ServerSentEvent:
        """Stream the events the user's permissions allow; see ``docs/realtime.md``.

        Every user may open the stream: what it carries is filtered by
        permission, as of the moment the stream opened.
        """
        return ServerSentEvent(
            event_stream(realtime, granted_permissions(request)),
            retry_duration=_RECONNECT_DELAY_MS,
        )
