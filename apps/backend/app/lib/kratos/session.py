"""Verification of browser sessions through the Kratos Public API."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from ory_kratos_client.api.frontend_api import FrontendApi
from ory_kratos_client.api.identity_api import IdentityApi

from app.config.kratos import KratosSettings
from app.lib.kratos.client import _SDKClient, _to_identity
from app.lib.kratos.exceptions import (
    KratosIdentityNotFoundError,
    KratosInvalidSessionError,
    KratosUnavailableError,
)
from app.lib.kratos.schemas import KratosIdentity

logger = structlog.get_logger()


class KratosSessionVerifier:
    """Resolve an active Kratos browser session from its Cookie header.

    Kratos never extends a session by itself, so a verified session that
    expires within ``session_extend_within`` is extended through the Admin API:
    the session ends only after its lifespan passes without requests.
    """

    def __init__(self, settings: KratosSettings) -> None:
        client = _SDKClient(
            base_url=settings.public_url,
            timeout=settings.public_timeout,
            concurrency=settings.public_concurrency,
        )
        admin = _SDKClient(
            base_url=settings.admin_url,
            timeout=settings.admin_timeout,
            concurrency=settings.admin_concurrency,
        )
        self._client = client
        self._api = FrontendApi(client.api_client)
        self._admin = admin
        self._identities = IdentityApi(admin.api_client)
        self._extend_within = settings.session_extend_within

    async def verify_session(self, *, cookie_header: str) -> KratosIdentity:
        session = await self._client.call(
            lambda: self._api.to_session(
                cookie=cookie_header,
                _request_timeout=self._client.timeout,
            ),
            invalid_session=True,
        )

        if session.active is not True or session.identity is None:
            raise KratosInvalidSessionError(
                detail="Kratos session is inactive or has no identity",
            )

        identity = _to_identity(session.identity)

        if not identity.is_active:
            raise KratosInvalidSessionError(detail="Kratos identity is inactive")

        if session.expires_at is not None and session.expires_at - datetime.now(UTC) < self._extend_within:
            await self._extend(session.id)

        return identity

    async def _extend(self, session_id: UUID) -> None:
        try:
            await self._admin.call(
                lambda: self._identities.extend_session(
                    id=str(session_id),
                    _request_timeout=self._admin.timeout,
                )
            )
        except (KratosUnavailableError, KratosIdentityNotFoundError):
            # The request is still authenticated; the next one tries again.
            # Kratos answers 404 to parallel requests extending the same session.
            logger.warning("kratos.session_extend_failed", session_id=str(session_id), exc_info=True)


__all__ = ("KratosSessionVerifier",)
