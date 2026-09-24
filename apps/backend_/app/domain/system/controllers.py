"""System domain controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from litestar import Controller, MediaType, get
from litestar.di import NamedDependency
from litestar.response import Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.domain.system import schemas as s

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.config.settings import AppSettings
    from app.lib.hydra import HydraClient
    from app.lib.kratos import KratosClient


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
