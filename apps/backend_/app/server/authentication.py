"""Production authentication middleware for browser requests."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import AbstractAsyncContextManager
from typing import Any, cast

from litestar.enums import ScopeType
from litestar.exceptions import NotAuthorizedException, ServiceUnavailableException
from litestar.middleware import ASGIMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.config.kratos import KratosSettings
from app.db import models as m
from app.lib.kratos import KratosSessionVerifier
from app.lib.kratos.exceptions import KratosInvalidSessionError, KratosUnavailableError

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


def _cookie_header(scope: Scope) -> str | None:
    scope_dict = cast(dict[str, object], scope)
    headers = cast(Iterable[tuple[bytes, bytes]], scope_dict.get("headers", ()))
    cookie_values = [value.decode("latin-1") for name, value in headers if name.lower() == b"cookie"]

    return "; ".join(cookie_values) or None


def _is_public_schema(scope: Scope) -> bool:
    path = scope["path"]

    return path == "/schema" or path.startswith("/schema/")


class KratosAuthenticationMiddleware(ASGIMiddleware):
    """Authenticate a request and put the local user in ``scope["user"]``."""

    scopes = (ScopeType.HTTP,)
    exclude_opt_key = "exclude_from_auth"
    should_bypass_for_scope = staticmethod(_is_public_schema)

    def __init__(
        self,
        *,
        verifier: KratosSessionVerifier,
        session_cookie: str,
        session_factory: SessionFactory,
    ) -> None:
        self._verifier = verifier
        self._session_cookie = session_cookie
        self._session_factory = session_factory

    async def handle(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        next_app: ASGIApp,
    ) -> None:
        cookie_header = _cookie_header(scope)
        if cookie_header is None or not self._has_session_cookie(cookie_header):
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

        if user is None or not user.identity_active or user.archived_at is not None:
            raise NotAuthorizedException(detail="Authentication required.")

        scope_dict = cast(dict[str, Any], scope)
        scope_dict["user"] = user
        await next_app(cast(Scope, scope_dict), receive, send)

    def _has_session_cookie(self, cookie_header: str) -> bool:
        prefix = f"{self._session_cookie}="

        return any(part.strip().startswith(prefix) for part in cookie_header.split(";"))


def create_authentication_middleware(settings: KratosSettings) -> KratosAuthenticationMiddleware:
    """Build the application authentication middleware from Kratos settings."""

    return KratosAuthenticationMiddleware(
        verifier=KratosSessionVerifier(settings),
        session_cookie=settings.session_cookie,
        session_factory=config.alchemy.get_session,
    )


__all__ = ("KratosAuthenticationMiddleware", "create_authentication_middleware")
