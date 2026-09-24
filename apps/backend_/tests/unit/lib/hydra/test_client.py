from unittest.mock import MagicMock

import pytest
from ory_hydra_client.exceptions import ApiException

from app.lib.hydra.client import _credentials, _introspection, _SDKClient
from app.lib.hydra.exceptions import (
    HydraClientAlreadyExistsError,
    HydraClientNotFoundError,
    HydraUnavailableError,
)

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.unit,
]


def test_credentials() -> None:
    credentials = _credentials(MagicMock(client_id="pak-client", client_secret="secret"))

    assert credentials.client.client_id == "pak-client"
    assert credentials.client_secret == "secret"


def test_credentials_without_secret() -> None:
    with pytest.raises(HydraUnavailableError):
        _credentials(MagicMock(client_id="pak-client", client_secret=None))


def test_introspection() -> None:
    introspection = _introspection(MagicMock(active=None, client_id="pak-client"))

    assert introspection.active is False
    assert introspection.client_id == "pak-client"


async def test_sdk_client_not_found() -> None:
    client = _SDKClient(base_url="http://hydra.test", timeout=1, concurrency=1)

    with pytest.raises(HydraClientNotFoundError):
        await client.call(MagicMock(side_effect=ApiException(status=404)))


async def test_sdk_client_already_exists() -> None:
    client = _SDKClient(base_url="http://hydra.test", timeout=1, concurrency=1)

    with pytest.raises(HydraClientAlreadyExistsError):
        await client.call(MagicMock(side_effect=ApiException(status=409)))


async def test_sdk_client_unavailable() -> None:
    client = _SDKClient(base_url="http://hydra.test", timeout=1, concurrency=1)

    with pytest.raises(HydraUnavailableError):
        await client.call(MagicMock(side_effect=OSError("connection refused")))
