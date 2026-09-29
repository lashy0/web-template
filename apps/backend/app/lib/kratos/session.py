"""Verification of browser sessions through the Kratos Public API."""

from __future__ import annotations

from ory_kratos_client.api.frontend_api import FrontendApi

from app.config.kratos import KratosSettings
from app.lib.kratos.client import _SDKClient, _to_identity
from app.lib.kratos.exceptions import KratosInvalidSessionError
from app.lib.kratos.schemas import KratosIdentity


class KratosSessionVerifier:
    """Resolve an active Kratos browser session from its Cookie header."""

    def __init__(self, settings: KratosSettings) -> None:
        client = _SDKClient(
            base_url=settings.public_url,
            timeout=settings.public_timeout,
            concurrency=settings.public_concurrency,
        )
        self._client = client
        self._api = FrontendApi(client.api_client)

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

        return identity


__all__ = ("KratosSessionVerifier",)
