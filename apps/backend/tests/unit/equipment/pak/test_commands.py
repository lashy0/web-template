from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.roles import Role
from app.contexts.equipment.pak.commands.create import CreatePak
from app.contexts.equipment.pak.commands.delete import DeletePak
from app.contexts.equipment.pak.contracts import PakOAuthClient, PakOAuthClientCredentials
from app.contexts.equipment.pak.exceptions import (
    PakCannotBeDeletedError,
    PakProvisioningError,
)
from app.contexts.equipment.pak.model import PakDevice, PakDeviceKind
from app.shared.security import CurrentPrincipal


class _Session:
    def begin(self) -> "_Session":
        return self

    def begin_nested(self) -> "_Session":
        return self

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class _SessionFactory:
    def __call__(self) -> _Session:
        return _Session()


def _principal() -> CurrentPrincipal:
    return CurrentPrincipal(
        user_id=uuid4(), identity_id=uuid4(), session_id=uuid4(), role=Role.ADMINISTRATOR
    )


def _cipher_key() -> SecretStr:
    return SecretStr(Fernet.generate_key().decode("ascii"))


@pytest.mark.unit
async def test_create_compensates_oauth_when_local_persistence_fails(mocker: MagicMock) -> None:
    repository = mocker.patch("app.contexts.equipment.pak.commands.create.PakRepository")
    repository.return_value.get_by_code = AsyncMock(return_value=None)
    repository.return_value.create = AsyncMock(side_effect=RuntimeError("database unavailable"))
    oauth = SimpleNamespace(
        create_client=AsyncMock(
            return_value=PakOAuthClientCredentials(PakOAuthClient("pak-created"), "access-key")
        ),
        delete_client=AsyncMock(),
    )
    command = CreatePak(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), oauth, _cipher_key()
    )

    with pytest.raises(PakProvisioningError):
        await command.execute(
            actor=_principal(), code="PAK-01", kind=PakDeviceKind.OTK_LINE, active=True
        )

    oauth.delete_client.assert_awaited_once_with("pak-created")


@pytest.mark.unit
async def test_create_oauth_failure_never_persists_local_pak(mocker: MagicMock) -> None:
    repository = mocker.patch("app.contexts.equipment.pak.commands.create.PakRepository")
    repository.return_value.get_by_code = AsyncMock(return_value=None)
    repository.return_value.create = AsyncMock()
    oauth = SimpleNamespace(create_client=AsyncMock(side_effect=RuntimeError("hydra unavailable")))
    command = CreatePak(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), oauth, _cipher_key()
    )

    with pytest.raises(RuntimeError, match="hydra unavailable"):
        await command.execute(
            actor=_principal(), code="PAK-01", kind=PakDeviceKind.OTK_LINE, active=True
        )

    repository.return_value.create.assert_not_awaited()


@pytest.mark.unit
async def test_delete_rejects_pak_with_quality_verification_history(mocker: MagicMock) -> None:
    repository = mocker.patch("app.contexts.equipment.pak.commands.delete.PakRepository")
    pak = PakDevice(
        id=uuid4(),
        code="PAK-01",
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id="pak-01",
        encrypted_access_key="encrypted",
        is_active=True,
    )
    repository.return_value.get_by_id = AsyncMock(return_value=pak)
    oauth = SimpleNamespace(delete_client=AsyncMock(), create_client=AsyncMock())
    history = MagicMock(
        return_value=SimpleNamespace(has_history_for_pak=AsyncMock(return_value=True))
    )
    command = DeletePak(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()), oauth, history, _cipher_key()
    )

    with pytest.raises(PakCannotBeDeletedError):
        await command.execute(actor=_principal(), pak_id=pak.id)

    oauth.delete_client.assert_not_awaited()
    repository.return_value.delete.assert_not_called()
