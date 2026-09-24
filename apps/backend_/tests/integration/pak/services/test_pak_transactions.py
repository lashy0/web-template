"""PAK changes stay consistent with Hydra across rollbacks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.db import models as m
from app.db.enums import PakDeviceKind
from app.domain.pak.crypto import PakAccessKeyCipher
from app.domain.pak.services import PakDeviceService
from app.lib.hydra import HydraClient
from app.lib.hydra.exceptions import HydraClientNotFoundError
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.integration.pak.conftest import CreatePak, IssueAccessToken

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
    pytest.mark.security,
]


async def test_rolled_back_creation_removes_hydra_client(
    session: AsyncSession,
    hydra_client: HydraClient,
    pak_service: PakDeviceService,
    pak_cipher: PakAccessKeyCipher,
) -> None:
    created: list[m.PakDevice] = []

    with pytest.raises(RuntimeError):
        async with unit_of_work(session) as uow:
            pak, _ = await pak_service.create_pak(
                {"code": "pak-rollback", "kind": PakDeviceKind.ENGINEERING, "is_active": True},
                hydra=hydra_client,
                cipher=pak_cipher,
                uow=uow,
            )
            created.append(pak)

            raise RuntimeError("request failed")

    assert await pak_service.get_by_id(created[0].id) is None

    with pytest.raises(HydraClientNotFoundError):
        await hydra_client.get_client(created[0].oauth_client_id)


async def test_rolled_back_rotation_keeps_previous_key(
    session: AsyncSession,
    hydra_client: HydraClient,
    pak_service: PakDeviceService,
    pak_cipher: PakAccessKeyCipher,
    create_pak: CreatePak,
    issue_access_token: IssueAccessToken,
) -> None:
    pak, key = await create_pak("pak-rotation-rollback")
    # The rollback expires loaded objects; keep plain values for the assertions.
    pak_id, client_id = pak.id, pak.oauth_client_id

    with pytest.raises(RuntimeError):
        async with unit_of_work(session) as uow:
            await pak_service.rotate_access_key(
                pak_id,
                hydra=hydra_client,
                cipher=pak_cipher,
                uow=uow,
            )

            raise RuntimeError("request failed")

    assert await pak_service.get_access_key(pak_id, cipher=pak_cipher) == key

    token = await issue_access_token(client_id, key)
    assert (await pak_service.authorize_machine_access_token(token, hydra=hydra_client)).id == pak_id
