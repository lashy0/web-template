from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar import Litestar

    from app.config import Settings
    from app.server.authentication import SessionVerifier


def create_app(
    *,
    settings: Settings | None = None,
    session_verifier: SessionVerifier | None = None,
) -> Litestar:
    """Build the application; without arguments it uses the environment settings.

    Args:
        settings: Settings to build the application from instead of the environment.
        session_verifier: Replacement for the Kratos check of browser sessions.
    """
    from litestar import Litestar

    from app.lib.openapi import OffsetPaginationSchemaPlugin
    from app.server.core import ApplicationCore

    return Litestar(
        plugins=[
            # Passed here rather than by ApplicationCore, so it precedes Litestar's
            # own schema plugins, which are added before any on_app_init runs.
            OffsetPaginationSchemaPlugin(),
            ApplicationCore(settings=settings, session_verifier=session_verifier),
        ]
    )
