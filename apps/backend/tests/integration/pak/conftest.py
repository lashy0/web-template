"""PAK domain integration test fixtures.

These fixtures provide the PAK service and helpers for tests against
PostgreSQL and a real Hydra.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, cast

import httpx
import pytest

from app.config import get_settings
from app.db import models as m
from app.db.enums import PakDeviceKind
from app.domain.pak.crypto import PakAccessKeyCipher
from app.domain.pak.services import PakDeviceService
from app.lib.hydra import HydraClient
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.conftest import HydraService


pytestmark = pytest.mark.anyio

type CreatePak = Callable[[str], Awaitable[tuple[m.PakDevice, str]]]
type IssueAccessToken = Callable[[str, str], Awaitable[str]]


@pytest.fixture
def pak_cipher() -> PakAccessKeyCipher:
    """Create the cipher configured for PAK access keys."""
    return PakAccessKeyCipher(get_settings().hydra.pak_access_key_encryption_key)


@pytest.fixture
async def pak_service(session: AsyncSession) -> AsyncGenerator[PakDeviceService]:
    """Create PakDeviceService instance with the test session."""
    async with PakDeviceService.new(session) as service:
        yield service


@pytest.fixture
def create_pak(
    session: AsyncSession,
    pak_service: PakDeviceService,
    hydra_client: HydraClient,
    pak_cipher: PakAccessKeyCipher,
) -> CreatePak:
    """Return a helper that commits an active engineering PAK with the given code."""

    async def _create(code: str) -> tuple[m.PakDevice, str]:
        async with unit_of_work(session) as uow:
            return await pak_service.create_pak(
                {"code": code, "kind": PakDeviceKind.ENGINEERING, "is_active": True},
                hydra=hydra_client,
                cipher=pak_cipher,
                uow=uow,
            )

    return _create


@pytest.fixture
def issue_access_token(hydra_service: HydraService) -> IssueAccessToken:
    """Return a helper that obtains a Hydra token as the PAK would."""

    async def _issue(client_id: str, client_secret: str) -> str:
        async with httpx.AsyncClient(base_url=hydra_service.public_url) as client:
            response = await client.post(
                "/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
            )
        response.raise_for_status()
        payload = cast("dict[str, Any]", response.json())

        return cast("str", payload["access_token"])

    return _issue
