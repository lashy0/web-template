from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import (
    AccessTokenIntrospection,
    OAuthClient,
    OAuthClientCredentials,
    OAuthClientManager,
    TokenIntrospector,
)
from app.auth.exceptions import ForbiddenError, OAuthClientNotFoundError
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.pak.crypto import PakAccessKeyCipher
from app.modules.pak.exceptions import (
    InvalidMachineAccessTokenError,
    PakCannotBeDeletedError,
    PakCredentialSynchronizationError,
    PakDeletionSynchronizationError,
    PakProvisioningError,
)
from app.modules.pak.models import PakDevice, PakDeviceKind
from app.modules.pak.service import PakManagementService


class _Session:
    def begin(self) -> _Session:
        return self

    async def __aenter__(self) -> _Session:
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


def _pak(*, encrypted_access_key: str = "ciphertext") -> PakDevice:
    return PakDevice(
        id=uuid4(),
        code="PAK-OTK-01",
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id="pak-test",
        encrypted_access_key=encrypted_access_key,
        is_active=True,
        archived_at=None,
    )


@pytest.fixture
def dependencies(mocker: MockerFixture) -> tuple[MagicMock, MagicMock]:
    repositories = mocker.patch("app.modules.pak.service.PakRepository")
    repositories.return_value.get_by_code = AsyncMock()
    repositories.return_value.get_by_id = AsyncMock()
    repositories.return_value.create = AsyncMock()
    repositories.return_value.update_details = AsyncMock()
    repositories.return_value.update_active = AsyncMock()
    repositories.return_value.update_archived = AsyncMock()
    repositories.return_value.update_access_key = AsyncMock()
    repositories.return_value.update_last_seen = AsyncMock(
        side_effect=lambda pak, *, last_seen_at: _set_last_seen_at(pak, last_seen_at)
    )
    repositories.return_value.get_by_oauth_client_id = AsyncMock()
    repositories.return_value.delete = AsyncMock()
    verification_sessions = mocker.patch("app.modules.pak.service.VerificationSessionRepository")
    verification_sessions.return_value.exists_by_pak_id = AsyncMock(return_value=False)
    audits = mocker.patch("app.modules.pak.service.AuditService")
    audits.from_session.return_value.record = AsyncMock()
    return repositories, audits


def _service(
    oauth_clients: object,
    token_introspector: object | None = None,
) -> PakManagementService:
    return PakManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()),
        cast(OAuthClientManager, oauth_clients),
        cast(
            TokenIntrospector,
            token_introspector or SimpleNamespace(introspect_access_token=AsyncMock()),
        ),
        SecretStr(Fernet.generate_key().decode("ascii")),
    )


@pytest.mark.unit
async def test_create_persists_only_the_encrypted_access_key(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, audits = dependencies
    pak = _pak()
    repositories.return_value.get_by_code.return_value = None
    repositories.return_value.create.return_value = pak
    credentials = OAuthClientCredentials(
        client=OAuthClient("pak-test", None, (), (), "client_secret_basic"),
        client_secret="plain-client-secret",
    )
    oauth_clients = SimpleNamespace(create_client=AsyncMock(return_value=credentials))
    service = _service(oauth_clients)

    created, access_key = await service.create(
        actor=_principal(), code=pak.code, kind=pak.kind, active=True
    )

    assert created is pak
    assert access_key == "plain-client-secret"
    assert set(oauth_clients.create_client.await_args.kwargs) == {"client_id"}
    assert oauth_clients.create_client.await_args.kwargs["client_id"].startswith("pak-")
    encrypted = repositories.return_value.create.await_args.kwargs["encrypted_access_key"]
    assert encrypted != "plain-client-secret"
    assert service._cipher().decrypt(encrypted) == "plain-client-secret"
    assert "plain-client-secret" not in str(audits.from_session.return_value.record.await_args)


@pytest.mark.unit
async def test_rotate_persists_new_encrypted_key_without_changing_client_id(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, audits = dependencies
    pak = _pak()
    repositories.return_value.get_by_id.return_value = pak
    repositories.return_value.update_access_key.return_value = pak
    credentials = OAuthClientCredentials(
        client=OAuthClient(pak.oauth_client_id, None, (), (), "client_secret_basic"),
        client_secret="rotated-secret",
    )
    restored_credentials = OAuthClientCredentials(
        client=OAuthClient(pak.oauth_client_id, None, (), (), "client_secret_basic"),
        client_secret="previous-secret",
    )
    oauth_clients = SimpleNamespace(
        rotate_client_credentials=AsyncMock(return_value=credentials),
        set_client_secret=AsyncMock(return_value=restored_credentials),
    )
    service = _service(oauth_clients)
    pak.encrypted_access_key = service._cipher().encrypt("previous-secret")

    access_key = await service.rotate_access_key(actor=_principal(), pak_id=pak.id)

    assert access_key == "rotated-secret"
    oauth_clients.rotate_client_credentials.assert_awaited_once_with(pak.oauth_client_id)
    encrypted = repositories.return_value.update_access_key.await_args.kwargs[
        "encrypted_access_key"
    ]
    assert encrypted != "rotated-secret"
    assert service._cipher().decrypt(encrypted) == "rotated-secret"
    assert pak.oauth_client_id == credentials.client.client_id
    assert "rotated-secret" not in str(audits.from_session.return_value.record.await_args)


@pytest.mark.unit
async def test_access_key_view_decrypts_key_and_audits_without_exposing_it(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, audits = dependencies
    encryption_key = Fernet.generate_key().decode("ascii")
    cipher = PakAccessKeyCipher(encryption_key)
    pak = _pak(encrypted_access_key=cipher.encrypt("stored-secret"))
    repositories.return_value.get_by_id.return_value = pak
    service = PakManagementService(
        cast(async_sessionmaker[AsyncSession], _SessionFactory()),
        cast(OAuthClientManager, SimpleNamespace()),
        cast(TokenIntrospector, SimpleNamespace()),
        SecretStr(encryption_key),
    )

    access_key = await service.get_access_key(actor=_principal(), pak_id=pak.id)

    assert access_key == "stored-secret"
    assert "stored-secret" not in str(audits.from_session.return_value.record.await_args)


@pytest.mark.unit
async def test_update_changes_pak_details_and_records_only_changed_fields(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, audits = dependencies
    pak = _pak()
    repositories.return_value.get_by_id.return_value = pak
    repositories.return_value.get_by_code.return_value = None

    async def update_details(
        item: PakDevice, *, code: str | None, kind: PakDeviceKind | None
    ) -> PakDevice:
        item.code = code or item.code
        item.kind = kind or item.kind
        return item

    repositories.return_value.update_details.side_effect = update_details
    service = _service(SimpleNamespace())

    updated = await service.update(
        actor=_principal(), pak_id=pak.id, code="PAK-OTK-02", kind=PakDeviceKind.ENGINEERING
    )

    assert (updated.code, updated.kind) == ("PAK-OTK-02", PakDeviceKind.ENGINEERING)
    record = audits.from_session.return_value.record.await_args.kwargs
    assert record["action"] == "pak.updated"
    assert record["old_data"] == {"code": "PAK-OTK-01", "kind": "otk_line"}
    assert record["new_data"] == {"code": "PAK-OTK-02", "kind": "engineering"}


@pytest.mark.unit
async def test_deactivation_and_archiving_immediately_mark_pak_inactive(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, audits = dependencies
    pak = _pak()
    repositories.return_value.get_by_id.return_value = pak

    async def update_active(item: PakDevice, *, active: bool) -> PakDevice:
        item.is_active = active
        return item

    async def update_archived(item: PakDevice, *, archived_at: object) -> PakDevice:
        item.archived_at = archived_at  # type: ignore[assignment]
        return item

    repositories.return_value.update_active.side_effect = update_active
    repositories.return_value.update_archived.side_effect = update_archived
    service = _service(SimpleNamespace())

    deactivated = await service.set_active(actor=_principal(), pak_id=pak.id, active=False)
    archived = await service.set_archived(actor=_principal(), pak_id=pak.id, archived=True)

    assert not deactivated.is_active
    assert archived.archived_at is not None
    assert not archived.is_active
    assert [
        call.kwargs["action"] for call in audits.from_session.return_value.record.await_args_list
    ] == [
        "pak.active_changed",
        "pak.archived",
    ]


@pytest.mark.unit
async def test_restoring_pak_does_not_reactivate_it(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, audits = dependencies
    pak = _pak()
    pak.is_active = False
    pak.archived_at = object()  # type: ignore[assignment]
    repositories.return_value.get_by_id.return_value = pak
    repositories.return_value.update_archived.side_effect = lambda item, *, archived_at: (
        _set_archived_at(item, archived_at)
    )
    service = _service(SimpleNamespace())

    restored = await service.set_archived(actor=_principal(), pak_id=pak.id, archived=False)

    assert restored.archived_at is None
    assert not restored.is_active
    assert audits.from_session.return_value.record.await_args.kwargs["action"] == "pak.restored"


@pytest.mark.unit
async def test_delete_removes_oauth_client_before_local_pak(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, audits = dependencies
    pak = _pak()
    repositories.return_value.get_by_id.return_value = pak
    oauth_clients = SimpleNamespace(delete_client=AsyncMock())
    service = _service(oauth_clients)

    await service.delete(actor=_principal(), pak_id=pak.id)

    oauth_clients.delete_client.assert_awaited_once_with(pak.oauth_client_id)
    repositories.return_value.delete.assert_awaited_once_with(pak)
    assert audits.from_session.return_value.record.await_args.kwargs["action"] == "pak.deleted"


@pytest.mark.unit
async def test_delete_rejects_pak_with_verification_history(
    dependencies: tuple[MagicMock, MagicMock], mocker: MockerFixture
) -> None:
    repositories, audits = dependencies
    pak = _pak()
    repositories.return_value.get_by_id.return_value = pak
    verification_sessions = mocker.patch("app.modules.pak.service.VerificationSessionRepository")
    verification_sessions.return_value.exists_by_pak_id = AsyncMock(return_value=True)
    oauth_clients = SimpleNamespace(delete_client=AsyncMock())
    service = _service(oauth_clients)

    with pytest.raises(PakCannotBeDeletedError):
        await service.delete(actor=_principal(), pak_id=pak.id)

    verification_sessions.return_value.exists_by_pak_id.assert_awaited_once_with(pak.id)
    oauth_clients.delete_client.assert_not_awaited()
    repositories.return_value.delete.assert_not_awaited()
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_rotation_reports_hydra_db_secret_synchronization_failure(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, audits = dependencies
    pak = _pak()
    repositories.return_value.get_by_id.return_value = pak
    repositories.return_value.update_access_key.side_effect = RuntimeError("database unavailable")
    credentials = OAuthClientCredentials(
        client=OAuthClient(pak.oauth_client_id, None, (), (), "client_secret_basic"),
        client_secret="rotated-secret",
    )
    restored_credentials = OAuthClientCredentials(
        client=OAuthClient(pak.oauth_client_id, None, (), (), "client_secret_basic"),
        client_secret="previous-secret",
    )
    oauth_clients = SimpleNamespace(
        rotate_client_credentials=AsyncMock(return_value=credentials),
        set_client_secret=AsyncMock(return_value=restored_credentials),
    )
    service = _service(oauth_clients)
    pak.encrypted_access_key = service._cipher().encrypt("previous-secret")

    with pytest.raises(PakCredentialSynchronizationError):
        await service.rotate_access_key(actor=_principal(), pak_id=pak.id)

    oauth_clients.rotate_client_credentials.assert_awaited_once_with(pak.oauth_client_id)
    oauth_clients.set_client_secret.assert_awaited_once_with(pak.oauth_client_id, "previous-secret")
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_delete_reports_when_hydra_is_deleted_but_db_delete_fails(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, _ = dependencies
    pak = _pak()
    repositories.return_value.get_by_id.return_value = pak
    repositories.return_value.delete.side_effect = RuntimeError("database unavailable")
    oauth_clients = SimpleNamespace(delete_client=AsyncMock(), create_client=AsyncMock())
    service = _service(oauth_clients)
    pak.encrypted_access_key = service._cipher().encrypt("previous-secret")

    with pytest.raises(PakDeletionSynchronizationError):
        await service.delete(actor=_principal(), pak_id=pak.id)

    oauth_clients.delete_client.assert_awaited_once_with(pak.oauth_client_id)
    oauth_clients.create_client.assert_awaited_once_with(
        client_id=pak.oauth_client_id,
        client_secret="previous-secret",
    )


@pytest.mark.unit
async def test_delete_removes_orphaned_local_pak_when_hydra_client_is_already_missing(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, _ = dependencies
    pak = _pak()
    repositories.return_value.get_by_id.return_value = pak
    oauth_clients = SimpleNamespace(delete_client=AsyncMock(side_effect=OAuthClientNotFoundError))
    service = _service(oauth_clients)

    await service.delete(actor=_principal(), pak_id=pak.id)

    repositories.return_value.delete.assert_awaited_once_with(pak)


@pytest.mark.unit
async def test_failed_local_pak_creation_rolls_back_oauth_client(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, _ = dependencies
    repositories.return_value.get_by_code.return_value = None
    repositories.return_value.create.side_effect = RuntimeError("database unavailable")
    credentials = OAuthClientCredentials(
        client=OAuthClient("pak-test", None, (), (), "client_secret_basic"),
        client_secret="plain-client-secret",
    )
    oauth_clients = SimpleNamespace(
        create_client=AsyncMock(return_value=credentials), delete_client=AsyncMock()
    )
    service = _service(oauth_clients)

    with pytest.raises(PakProvisioningError):
        await service.create(
            actor=_principal(), code="PAK-OTK-01", kind=PakDeviceKind.OTK_LINE, active=True
        )

    oauth_clients.delete_client.assert_awaited_once_with(credentials.client.client_id)


@pytest.mark.unit
async def test_machine_token_is_rejected_when_pak_is_inactive(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, _ = dependencies
    pak = _pak()
    pak.is_active = False
    repositories.return_value.get_by_oauth_client_id.return_value = pak
    introspector = SimpleNamespace(
        introspect_access_token=AsyncMock(
            return_value=AccessTokenIntrospection(True, pak.oauth_client_id, ())
        )
    )
    service = _service(SimpleNamespace(), introspector)

    with pytest.raises(ForbiddenError, match="inactive or archived"):
        await service.authorize_machine_access_token("valid-token")


@pytest.mark.unit
async def test_machine_token_is_rejected_when_pak_is_archived(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, _ = dependencies
    pak = _pak()
    pak.archived_at = object()  # type: ignore[assignment]
    repositories.return_value.get_by_oauth_client_id.return_value = pak
    introspector = SimpleNamespace(
        introspect_access_token=AsyncMock(
            return_value=AccessTokenIntrospection(True, pak.oauth_client_id, ())
        )
    )
    service = _service(SimpleNamespace(), introspector)

    with pytest.raises(ForbiddenError, match="inactive or archived"):
        await service.authorize_machine_access_token("valid-token")


@pytest.mark.unit
async def test_machine_token_is_authorized_and_updates_missing_last_seen_at(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, _ = dependencies
    pak = _pak()
    repositories.return_value.get_by_oauth_client_id.return_value = pak
    introspector = SimpleNamespace(
        introspect_access_token=AsyncMock(
            return_value=AccessTokenIntrospection(True, pak.oauth_client_id, ())
        )
    )
    service = _service(SimpleNamespace(), introspector)

    authorized = await service.authorize_machine_access_token("valid-token")

    assert authorized is pak
    introspector.introspect_access_token.assert_awaited_once_with("valid-token")
    repositories.return_value.update_last_seen.assert_awaited_once()
    assert repositories.return_value.update_last_seen.await_args.args == (pak,)
    assert repositories.return_value.update_last_seen.await_args.kwargs["last_seen_at"] is not None


@pytest.mark.unit
async def test_machine_token_authorization_does_not_update_recent_last_seen_at(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, _ = dependencies
    pak = _pak()
    pak.last_seen_at = datetime.now(UTC)
    repositories.return_value.get_by_oauth_client_id.return_value = pak
    introspector = SimpleNamespace(
        introspect_access_token=AsyncMock(
            return_value=AccessTokenIntrospection(True, pak.oauth_client_id, ())
        )
    )
    service = _service(SimpleNamespace(), introspector)

    authorized = await service.authorize_machine_access_token("valid-token")

    assert authorized is pak
    repositories.return_value.update_last_seen.assert_not_awaited()


@pytest.mark.unit
async def test_machine_token_without_active_oauth_session_is_rejected(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, _ = dependencies
    introspector = SimpleNamespace(
        introspect_access_token=AsyncMock(
            return_value=AccessTokenIntrospection(False, "pak-test", ())
        )
    )
    service = _service(SimpleNamespace(), introspector)

    with pytest.raises(InvalidMachineAccessTokenError):
        await service.authorize_machine_access_token("expired-token")

    repositories.return_value.get_by_oauth_client_id.assert_not_awaited()


def _set_archived_at(pak: PakDevice, archived_at: object) -> PakDevice:
    pak.archived_at = archived_at  # type: ignore[assignment]
    return pak


def _set_last_seen_at(pak: PakDevice, last_seen_at: datetime) -> PakDevice:
    pak.last_seen_at = last_seen_at
    return pak
