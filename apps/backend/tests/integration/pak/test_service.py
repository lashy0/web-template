import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import func, select

from app.auth.contracts import OAuthClient, OAuthClientCredentials
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.audit.models import AuditEvent
from app.modules.audit.service import AuditService
from app.modules.pak.crypto import PakAccessKeyCipher
from app.modules.pak.exceptions import (
    PakCredentialSynchronizationError,
    PakDeletionSynchronizationError,
)
from app.modules.pak.models import PakDevice, PakDeviceKind
from app.modules.pak.repository import PakRepository
from app.modules.pak.services import PakManagementService

pytestmark = pytest.mark.integration


@pytest.fixture
async def scenario(database_session_factory):
    factory = database_session_factory
    key = SecretStr(Fernet.generate_key().decode())
    cipher = PakAccessKeyCipher(key.get_secret_value())
    pak = PakDevice(
        id=uuid4(),
        code=uuid4().hex,
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id=uuid4().hex,
        encrypted_access_key=cipher.encrypt("original"),
        is_active=True,
    )
    async with factory() as session, session.begin():
        session.add(pak)
    oauth = AsyncMock()
    client = OAuthClient(
        client_id=pak.oauth_client_id,
        name=None,
        grant_types=(),
        scopes=(),
        token_endpoint_auth_method=None,
    )
    oauth.rotate_client_credentials.return_value = OAuthClientCredentials(client, "rotated")
    oauth.set_client_secret.return_value = OAuthClientCredentials(client, "original")
    service = PakManagementService(factory, oauth, AsyncMock(), key)
    actor = CurrentPrincipal(
        user_id=uuid4(), identity_id=uuid4(), session_id=uuid4(), role=Role.ADMINISTRATOR
    )
    return factory, pak, oauth, service, actor, cipher, client


@pytest.mark.parametrize("operation", ["rotate", "delete"])
async def test_provider_change_is_compensated_on_audit_failure(scenario, mocker, operation):
    factory, pak, oauth, service, actor, cipher, _ = scenario
    mocker.patch.object(AuditService, "record", side_effect=RuntimeError("audit unavailable"))
    if operation == "rotate":
        with pytest.raises(PakCredentialSynchronizationError):
            await service.rotate_access_key(actor=actor, pak_id=pak.id)
        oauth.set_client_secret.assert_awaited_once_with(pak.oauth_client_id, "original")
    else:
        with pytest.raises(PakDeletionSynchronizationError):
            await service.delete(actor=actor, pak_id=pak.id)
        oauth.create_client.assert_awaited_once_with(
            client_id=pak.oauth_client_id, client_secret="original"
        )
    saved = await service.get(pak.id)
    assert cipher.decrypt(saved.encrypted_access_key) == "original"
    async with factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.entity_id == str(pak.id))
            )
            == 0
        )


@pytest.mark.parametrize("compensate", [False, True])
async def test_concurrent_rotations_are_serialized_before_provider_call(
    scenario, monkeypatch, compensate
):
    factory, pak, oauth, service, actor, cipher, client = scenario
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = []

    async def rotate(client_id):
        calls.append(client_id)
        if len(calls) == 1 and not compensate:
            entered.set()
            await release.wait()
        return OAuthClientCredentials(client, f"secret-{len(calls)}")

    oauth.rotate_client_credentials.side_effect = rotate
    if compensate:
        original_record = AuditService.record
        failed = False

        async def record(service, **kwargs):
            nonlocal failed
            if not failed:
                failed = True
                raise RuntimeError("audit unavailable")
            return await original_record(service, **kwargs)

        async def restore(client_id, secret):
            assert client_id == client.client_id
            entered.set()
            await release.wait()
            return OAuthClientCredentials(client, secret)

        monkeypatch.setattr(AuditService, "record", record)
        oauth.set_client_secret.side_effect = restore
    original = PakRepository.get_by_id
    pids = []

    async def get(repository, pak_id, *, for_update=False):
        if for_update:
            pids.append(await repository._session.scalar(select(func.pg_backend_pid())))
        return await original(repository, pak_id, for_update=for_update)

    monkeypatch.setattr(PakRepository, "get_by_id", get)
    first = asyncio.create_task(service.rotate_access_key(actor=actor, pak_id=pak.id))
    try:
        await asyncio.wait_for(entered.wait(), 5)
        second = asyncio.create_task(service.rotate_access_key(actor=actor, pak_id=pak.id))

        async def wait_for_block():
            async with factory() as session:
                while len(pids) < 2 or not await session.scalar(
                    select(func.pg_blocking_pids(pids[1]))
                ):
                    await asyncio.sleep(0.01)

        await asyncio.wait_for(wait_for_block(), 5)
        assert len(calls) == 1
    finally:
        release.set()
    results = await asyncio.gather(first, second, return_exceptions=True)
    if compensate:
        assert isinstance(results[0], PakCredentialSynchronizationError)
    else:
        assert results[0] == "secret-1"
    assert results[1] == "secret-2"
    assert cipher.decrypt((await service.get(pak.id)).encrypted_access_key) == "secret-2"
