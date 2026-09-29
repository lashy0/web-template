"""Resources a background task worker shares between its jobs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Required

from saq.types import Context

from app.config import get_settings

if TYPE_CHECKING:
    from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig

    from app.config import Settings


class WorkerContext(Context, total=False):
    """The SAQ context of this application's tasks; :func:`on_startup` fills it before any job runs."""

    settings: Required[Settings]
    alchemy: Required[SQLAlchemyAsyncConfig]


async def on_startup(ctx: WorkerContext) -> None:
    """Open the database engine once per worker process."""
    settings = get_settings()
    ctx["settings"] = settings
    ctx["alchemy"] = settings.db.get_config()


async def on_shutdown(ctx: WorkerContext) -> None:
    if "alchemy" in ctx:
        await ctx["alchemy"].get_engine().dispose()


__all__ = ("WorkerContext", "on_shutdown", "on_startup")
