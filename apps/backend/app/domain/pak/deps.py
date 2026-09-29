"""PAK domain dependencies."""

from __future__ import annotations

from typing import Any

from litestar import Request
from litestar.di import NamedDependency
from litestar.exceptions import NotAuthorizedException

from app.config import HydraSettings
from app.db import models as m
from app.domain.pak.crypto import PakAccessKeyCipher
from app.domain.pak.services import PakDeviceService
from app.lib.deps import create_service_provider
from app.lib.exceptions import AuthenticationError
from app.lib.hydra import HydraClient

provide_pak_devices_service = create_service_provider(
    PakDeviceService,
    error_messages={
        "duplicate_key": "PAK device already exists.",
        "integrity": "PAK device operation failed.",
    },
)


def provide_pak_access_key_cipher(
    hydra_settings: NamedDependency[HydraSettings],
) -> PakAccessKeyCipher:
    """Build the cipher for stored PAK OAuth client secrets."""
    return PakAccessKeyCipher(hydra_settings.pak_access_key_encryption_key)


def _bearer_token(request: Request[Any, Any, Any]) -> str | None:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    token = token.strip()

    if scheme.lower() != "bearer" or not token:
        return None

    return token


async def provide_current_pak(
    request: Request[Any, Any, Any],
    pak_devices_service: NamedDependency[PakDeviceService],
    hydra: NamedDependency[HydraClient],
) -> m.PakDevice:
    """Authenticate a machine request by its Hydra bearer token."""
    token = _bearer_token(request)

    if token is None:
        raise NotAuthorizedException(
            detail="PAK access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return await pak_devices_service.authorize_machine_access_token(token, hydra=hydra)
    except AuthenticationError as exc:
        raise NotAuthorizedException(
            detail=exc.detail,
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        ) from exc


__all__ = (
    "provide_current_pak",
    "provide_pak_access_key_cipher",
    "provide_pak_devices_service",
)
