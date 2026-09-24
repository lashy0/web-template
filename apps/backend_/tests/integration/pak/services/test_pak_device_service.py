"""PAK device service integration tests against PostgreSQL and Hydra."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.domain.pak.crypto import PakAccessKeyCipher
from app.domain.pak.services import PakDeviceService
from app.lib.exceptions import AuthenticationError
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


async def test_create_pak_provisions_hydra_client(
    hydra_client: HydraClient,
    pak_cipher: PakAccessKeyCipher,
    create_pak: CreatePak,
) -> None:
    pak, key = await create_pak("pak-create")

    assert (await hydra_client.get_client(pak.oauth_client_id)).client_id == pak.oauth_client_id
    assert pak_cipher.decrypt(pak.encrypted_access_key) == key


async def test_access_token_authenticates_pak(
    session: AsyncSession,
    hydra_client: HydraClient,
    pak_service: PakDeviceService,
    create_pak: CreatePak,
    issue_access_token: IssueAccessToken,
) -> None:
    pak, key = await create_pak("pak-auth")
    token = await issue_access_token(pak.oauth_client_id, key)

    async with unit_of_work(session):
        authenticated = await pak_service.authorize_machine_access_token(token, hydra=hydra_client)

    assert authenticated.id == pak.id
    assert authenticated.last_seen_at is not None


async def test_deactivated_pak_is_rejected(
    session: AsyncSession,
    hydra_client: HydraClient,
    pak_service: PakDeviceService,
    create_pak: CreatePak,
    issue_access_token: IssueAccessToken,
) -> None:
    pak, key = await create_pak("pak-deactivate")
    token = await issue_access_token(pak.oauth_client_id, key)

    async with unit_of_work(session) as uow:
        await pak_service.set_active(pak.id, is_active=False, hydra=hydra_client, uow=uow)

    assert (await hydra_client.introspect_access_token(token)).active is False

    with pytest.raises(AuthenticationError):
        await pak_service.authorize_machine_access_token(token, hydra=hydra_client)


async def test_reactivated_pak_authenticates_again(
    session: AsyncSession,
    hydra_client: HydraClient,
    pak_service: PakDeviceService,
    create_pak: CreatePak,
    issue_access_token: IssueAccessToken,
) -> None:
    pak, key = await create_pak("pak-reactivate")

    async with unit_of_work(session) as uow:
        await pak_service.set_active(
            pak.id,
            is_active=False,
            hydra=hydra_client,
            uow=uow,
        )
    async with unit_of_work(session) as uow:
        await pak_service.set_active(
            pak.id,
            is_active=True,
            hydra=hydra_client,
            uow=uow,
        )

    token = await issue_access_token(pak.oauth_client_id, key)
    assert (await pak_service.authorize_machine_access_token(token, hydra=hydra_client)).id == pak.id


async def test_rotate_access_key_revokes_previous_token(
    session: AsyncSession,
    hydra_client: HydraClient,
    pak_service: PakDeviceService,
    pak_cipher: PakAccessKeyCipher,
    create_pak: CreatePak,
    issue_access_token: IssueAccessToken,
) -> None:
    pak, key = await create_pak("pak-rotate")
    old_token = await issue_access_token(pak.oauth_client_id, key)

    async with unit_of_work(session) as uow:
        _, new_key = await pak_service.rotate_access_key(
            pak.id,
            hydra=hydra_client,
            cipher=pak_cipher,
            uow=uow,
        )

    assert new_key != key
    assert await pak_service.get_access_key(pak.id, cipher=pak_cipher) == new_key
    assert (await hydra_client.introspect_access_token(old_token)).active is False

    new_token = await issue_access_token(pak.oauth_client_id, new_key)
    assert (await pak_service.authorize_machine_access_token(new_token, hydra=hydra_client)).id == pak.id


async def test_archived_pak_is_rejected(
    session: AsyncSession,
    hydra_client: HydraClient,
    pak_service: PakDeviceService,
    create_pak: CreatePak,
    issue_access_token: IssueAccessToken,
) -> None:
    pak, key = await create_pak("pak-archive")
    token = await issue_access_token(pak.oauth_client_id, key)

    async with unit_of_work(session) as uow:
        await pak_service.set_archived(pak.id, archived=True, hydra=hydra_client, uow=uow)

    assert (await hydra_client.introspect_access_token(token)).active is False

    with pytest.raises(AuthenticationError):
        await pak_service.authorize_machine_access_token(token, hydra=hydra_client)


async def test_delete_pak_removes_hydra_client(
    session: AsyncSession,
    hydra_client: HydraClient,
    pak_service: PakDeviceService,
    create_pak: CreatePak,
) -> None:
    pak, _ = await create_pak("pak-delete")

    async with unit_of_work(session) as uow:
        await pak_service.delete_pak(pak.id, hydra=hydra_client, uow=uow)

    assert await pak_service.get_by_id(pak.id) is None

    with pytest.raises(HydraClientNotFoundError):
        await hydra_client.get_client(pak.oauth_client_id)
