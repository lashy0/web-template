"""Production authentication middleware for browser requests."""

from __future__ import annotations

import re
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol

from litestar.connection import ASGIConnection
from litestar.enums import ScopeType
from litestar.exceptions import NotAuthorizedException, ServiceUnavailableException
from litestar.middleware import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
    DefineMiddleware,
)
from litestar.types import ASGIApp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.kratos import KratosSettings
from app.db import models as m
from app.lib.kratos import KratosSessionVerifier
from app.lib.kratos.exceptions import KratosInvalidSessionError, KratosUnavailableError
from app.lib.kratos.schemas import KratosIdentity
from app.server.paths import SCHEMA_PATH

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]

_PUBLIC_PATHS = rf"^{re.escape(SCHEMA_PATH)}(/|$)"
"""The OpenAPI document and its Scalar page."""


class SessionVerifier(Protocol):
    """Resolve a browser ``Cookie`` header to the Kratos identity it belongs to.

    Raises ``KratosInvalidSessionError`` for a missing or expired session and
    ``KratosUnavailableError`` when Kratos cannot answer.
    """

    async def verify_session(
        self,
        *,
        cookie_header: str,
    ) -> KratosIdentity: ...


class KratosAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    """Authenticate a request by its Kratos session.

    The local user goes to ``scope["user"]`` and the Kratos identity to
    ``scope["auth"]``. Routes with ``exclude_from_auth``, the public paths and
    ``OPTIONS`` requests (CORS preflights) are not authenticated.
    """

    __slots__ = ("_session_cookie", "_session_factory", "_verifier")

    def __init__(
        self,
        app: ASGIApp,
        *,
        verifier: SessionVerifier,
        session_cookie: str,
        session_factory: SessionFactory,
    ) -> None:
        super().__init__(app, exclude=_PUBLIC_PATHS, scopes={ScopeType.HTTP})
        self._verifier = verifier
        self._session_cookie = session_cookie
        self._session_factory = session_factory

    async def authenticate_request(
        self,
        connection: ASGIConnection[Any, Any, Any, Any],
    ) -> AuthenticationResult:
        cookie_header = connection.headers.get("cookie")

        if cookie_header is None or self._session_cookie not in connection.cookies:
            raise NotAuthorizedException(detail="Authentication required.")

        try:
            identity = await self._verifier.verify_session(cookie_header=cookie_header)
        except KratosInvalidSessionError as exc:
            raise NotAuthorizedException(detail="Authentication required.") from exc
        except KratosUnavailableError as exc:
            raise ServiceUnavailableException(detail="Authentication provider unavailable.") from exc

        async with self._session_factory() as session:
            user = await session.scalar(
                select(m.User).where(
                    m.User.identity_id == identity.id,
                    m.User.identity_active.is_(True),
                    m.User.archived_at.is_(None),
                )
            )

        if user is None:
            raise NotAuthorizedException(detail="Authentication required.")

        return AuthenticationResult(user=user, auth=identity)


def create_authentication_middleware(
    settings: KratosSettings,
    *,
    session_factory: SessionFactory,
    verifier: SessionVerifier | None = None,
) -> DefineMiddleware:
    """Build the authentication middleware; ``verifier`` defaults to the Kratos Public API."""

    return DefineMiddleware(
        KratosAuthenticationMiddleware,
        verifier=verifier or KratosSessionVerifier(settings),
        session_cookie=settings.session_cookie,
        session_factory=session_factory,
    )


__all__ = (
    "KratosAuthenticationMiddleware",
    "SessionVerifier",
    "create_authentication_middleware",
)
