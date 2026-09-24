from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from ory_kratos_client.exceptions import ApiException

from app.lib.kratos.client import _SDKClient, _to_identity
from app.lib.kratos.exceptions import (
    KratosIdentityAlreadyExistsError,
    KratosIdentityNotFoundError,
    KratosInvalidSessionError,
    KratosUnavailableError,
)

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.unit,
]


def test_to_identity_reads_login_and_state() -> None:
    identity_id = uuid4()
    sdk_identity = MagicMock(
        id=str(identity_id),
        traits={"login": "operator"},
        state="active",
        metadata_admin=None,
    )

    identity = _to_identity(sdk_identity)

    assert identity.id == identity_id
    assert identity.login == "operator"
    assert identity.is_active is True


def test_to_identity_without_login_is_unavailable() -> None:
    sdk_identity = MagicMock(id=str(uuid4()), traits={}, state="active", metadata_admin=None)

    with pytest.raises(KratosUnavailableError):
        _to_identity(sdk_identity)


async def test_sdk_client_not_found() -> None:
    client = _SDKClient(base_url="http://kratos.test", timeout=1, concurrency=1)

    with pytest.raises(KratosIdentityNotFoundError):
        await client.call(MagicMock(side_effect=ApiException(status=404)))


async def test_sdk_client_already_exists() -> None:
    client = _SDKClient(base_url="http://kratos.test", timeout=1, concurrency=1)

    with pytest.raises(KratosIdentityAlreadyExistsError):
        await client.call(MagicMock(side_effect=ApiException(status=409)))


async def test_sdk_client_invalid_session() -> None:
    client = _SDKClient(base_url="http://kratos.test", timeout=1, concurrency=1)

    with pytest.raises(KratosInvalidSessionError):
        await client.call(MagicMock(side_effect=ApiException(status=401)), invalid_session=True)


async def test_sdk_client_unavailable() -> None:
    client = _SDKClient(base_url="http://kratos.test", timeout=1, concurrency=1)

    with pytest.raises(KratosUnavailableError):
        await client.call(MagicMock(side_effect=OSError("connection refused")))
