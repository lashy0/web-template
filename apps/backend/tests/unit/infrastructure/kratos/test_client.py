from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from ory_kratos_client.exceptions import ApiException
from ory_kratos_client.models.identity import Identity as KratosIdentity

from app.auth.exceptions import (
    IdentityAlreadyExistsError,
    IdentityNotFoundError,
    IdentityProviderUnavailableError,
    InvalidSessionError,
)
from app.infrastructure.kratos.client import (
    KratosIdentityManager,
    KratosSessionVerifier,
    _identity,
    _SdkClient,
)


def _raise(exception: Exception) -> None:
    raise exception


@pytest.mark.unit
@pytest.mark.parametrize(
    ("status", "error"),
    [
        pytest.param(401, InvalidSessionError, id="unauthorized"),
        pytest.param(403, InvalidSessionError, id="forbidden"),
        pytest.param(404, IdentityNotFoundError, id="not-found"),
        pytest.param(409, IdentityAlreadyExistsError, id="conflict"),
        pytest.param(500, IdentityProviderUnavailableError, id="server-error"),
    ],
)
async def test_sdk_client_maps_kratos_api_errors(status: int, error: type[Exception]) -> None:
    client = _SdkClient(base_url="http://kratos:4434", timeout=1.0, concurrency=1)

    with pytest.raises(error):
        await client.call(lambda: _raise(ApiException(status=status)))


@pytest.mark.unit
async def test_sdk_client_maps_network_errors_to_unavailable() -> None:
    client = _SdkClient(base_url="http://kratos:4434", timeout=1.0, concurrency=1)

    with pytest.raises(IdentityProviderUnavailableError):
        await client.call(lambda: _raise(OSError("Kratos is unavailable")))


@pytest.mark.unit
def test_identity_maps_kratos_traits_and_state() -> None:
    identity_id = uuid4()

    result = _identity(
        cast(
            KratosIdentity,
            SimpleNamespace(
                id=str(identity_id),
                traits={"login": "alice"},
                state="active",
                metadata_admin={"provisioning": {"owner": "backend"}},
            ),
        )
    )

    assert result.id == identity_id
    assert result.login == "alice"
    assert result.active is True
    assert result.metadata == {"provisioning": {"owner": "backend"}}


@pytest.mark.unit
async def test_session_verifier_forwards_only_the_session_cookie() -> None:
    identity_id = uuid4()
    session_id = uuid4()
    expires_at = datetime.now(UTC)
    verifier = object.__new__(KratosSessionVerifier)
    client = SimpleNamespace(
        timeout=2.0,
        call=AsyncMock(side_effect=lambda operation: operation()),
    )
    api = MagicMock()
    object.__setattr__(verifier, "_client", client)
    object.__setattr__(verifier, "_api", api)
    api.to_session.return_value = SimpleNamespace(
        id=str(session_id),
        expires_at=expires_at,
        identity=SimpleNamespace(
            id=str(identity_id), traits={"login": "alice"}, state="active", metadata_admin=None
        ),
    )

    session = await verifier.verify_session(cookie_header="ory_kratos_session=opaque-value")

    assert session.id == session_id
    assert session.identity.id == identity_id
    api.to_session.assert_called_once_with(
        cookie="ory_kratos_session=opaque-value", _request_timeout=2.0
    )


@pytest.mark.unit
async def test_session_verifier_rejects_incomplete_kratos_session() -> None:
    verifier = object.__new__(KratosSessionVerifier)
    client = SimpleNamespace(
        timeout=2.0,
        call=AsyncMock(side_effect=lambda operation: operation()),
    )
    api = MagicMock()
    object.__setattr__(verifier, "_client", client)
    object.__setattr__(verifier, "_api", api)
    api.to_session.return_value = SimpleNamespace(identity=None, expires_at=None)

    with pytest.raises(IdentityProviderUnavailableError):
        await verifier.verify_session(cookie_header="ory_kratos_session=opaque-value")


@pytest.mark.unit
async def test_identity_manager_creates_backend_owned_inactive_identity() -> None:
    identity_id = uuid4()
    user_id = uuid4()
    manager = object.__new__(KratosIdentityManager)
    client = SimpleNamespace(
        timeout=10.0,
        call=AsyncMock(side_effect=lambda operation: operation()),
    )
    identities = MagicMock()
    object.__setattr__(manager, "_client", client)
    object.__setattr__(manager, "_identities", identities)
    identities.create_identity.return_value = SimpleNamespace(
        id=str(identity_id), traits={"login": "alice"}, state="inactive", metadata_admin=None
    )

    identity = await manager.create_identity(
        login="alice", password="correct-horse-battery-staple", active=False, user_id=user_id
    )

    assert identity.id == identity_id
    assert identity.active is False
    body = identities.create_identity.call_args.kwargs["create_identity_body"]
    assert body.state == "inactive"
    assert body.traits == {"login": "alice"}
    assert body.external_id == str(user_id)
    assert body.metadata_admin == {
        "provisioning": {
            "owner": "backend",
            "version": 1,
            "kind": "standard",
            "user_id": str(user_id),
        }
    }


@pytest.mark.unit
async def test_identity_manager_readiness_is_false_when_kratos_is_unavailable() -> None:
    manager = object.__new__(KratosIdentityManager)
    client = SimpleNamespace(
        timeout=10.0,
        call=AsyncMock(side_effect=IdentityProviderUnavailableError),
    )
    object.__setattr__(manager, "_client", client)
    object.__setattr__(manager, "_metadata", MagicMock())

    assert await manager.is_ready() is False


@pytest.mark.unit
async def test_identity_manager_ignores_missing_sessions_when_revoking() -> None:
    manager = object.__new__(KratosIdentityManager)
    client = SimpleNamespace(
        timeout=10.0,
        call=AsyncMock(side_effect=IdentityNotFoundError),
    )
    object.__setattr__(manager, "_client", client)
    object.__setattr__(manager, "_identities", MagicMock())

    await manager.revoke_all_sessions(uuid4())

    client.call.assert_awaited_once()


@pytest.mark.unit
async def test_identity_manager_ignores_missing_identity_when_deleting() -> None:
    manager = object.__new__(KratosIdentityManager)
    client = SimpleNamespace(
        timeout=10.0,
        call=AsyncMock(side_effect=IdentityNotFoundError),
    )
    object.__setattr__(manager, "_client", client)
    object.__setattr__(manager, "_identities", MagicMock())

    await manager.delete_identity(uuid4())

    client.call.assert_awaited_once()
