from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from ory_hydra_client.exceptions import ApiException
from ory_hydra_client.models.introspected_o_auth2_token import IntrospectedOAuth2Token
from ory_hydra_client.models.o_auth2_client import OAuth2Client as HydraOAuth2Client

from app.auth.exceptions import (
    OAuthClientAlreadyExistsError,
    OAuthClientNotFoundError,
    OAuthProviderUnavailableError,
)
from app.infrastructure.hydra.client import (
    HydraOAuthClientManager,
    HydraTokenIntrospector,
    _credentials,
    _introspection,
    _oauth_client,
    _SdkClient,
)


def _raise(exception: Exception) -> None:
    raise exception


@pytest.mark.unit
@pytest.mark.parametrize(
    ("status", "error"),
    [
        pytest.param(404, OAuthClientNotFoundError, id="not-found"),
        pytest.param(409, OAuthClientAlreadyExistsError, id="conflict"),
        pytest.param(500, OAuthProviderUnavailableError, id="server-error"),
    ],
)
async def test_sdk_client_maps_hydra_api_errors(status: int, error: type[Exception]) -> None:
    client = _SdkClient(base_url="http://hydra:4445", timeout=1.0, concurrency=1)

    with pytest.raises(error):
        await client.call(lambda: _raise(ApiException(status=status)))


@pytest.mark.unit
async def test_sdk_client_runs_sync_operation_outside_the_event_loop() -> None:
    client = _SdkClient(base_url="http://hydra:4445", timeout=1.0, concurrency=1)

    assert await client.call(lambda: "complete") == "complete"


@pytest.mark.unit
def test_hydra_models_are_mapped_to_project_contracts() -> None:
    client = _oauth_client(
        HydraOAuth2Client(
            client_id="machine-client",
            client_name="Machine client",
            grant_types=["client_credentials"],
            scope="orders:read orders:write",
        )
    )
    credentials = _credentials(
        HydraOAuth2Client(
            client_id="machine-client",
            client_secret="cleartext-returned-once",
            grant_types=["client_credentials"],
        )
    )
    introspection = _introspection(
        IntrospectedOAuth2Token(
            active=True,
            client_id="machine-client",
            scope="orders:read orders:write",
        )
    )

    assert client.client_id == "machine-client"
    assert client.scopes == ("orders:read", "orders:write")
    assert credentials.client_secret == "cleartext-returned-once"
    assert introspection.active is True
    assert introspection.client_id == "machine-client"
    assert introspection.scopes == ("orders:read", "orders:write")


@pytest.mark.unit
async def test_client_manager_creates_client_credentials_client() -> None:
    manager = object.__new__(HydraOAuthClientManager)
    sdk_client = SimpleNamespace(
        timeout=10.0,
        call=AsyncMock(side_effect=lambda operation: operation()),
    )
    oauth2 = MagicMock()
    oauth2.create_o_auth2_client.side_effect = lambda **kwargs: HydraOAuth2Client(
        client_id="machine-client",
        client_secret=kwargs["o_auth2_client"].client_secret,
        grant_types=["client_credentials"],
        scope="orders:read",
    )
    object.__setattr__(manager, "_client", sdk_client)
    object.__setattr__(manager, "_oauth2", oauth2)

    credentials = await manager.create_client(
        client_id="machine-client",
        name="Machine client",
        scopes=("orders:read",),
    )

    assert credentials.client.client_id == "machine-client"
    body = oauth2.create_o_auth2_client.call_args.kwargs["o_auth2_client"]
    assert body.grant_types == ["client_credentials"]
    assert body.scope == "orders:read"
    assert body.token_endpoint_auth_method == "client_secret_basic"
    assert body.client_secret is not None
    assert len(body.client_secret) >= 64
    assert credentials.client_secret == body.client_secret


@pytest.mark.unit
async def test_client_manager_rotates_a_secret_without_changing_client_identity() -> None:
    manager = object.__new__(HydraOAuthClientManager)
    sdk_client = SimpleNamespace(
        timeout=10.0,
        call=AsyncMock(side_effect=lambda operation: operation()),
    )
    oauth2 = MagicMock()
    oauth2.get_o_auth2_client.return_value = HydraOAuth2Client(
        client_id="machine-client",
        grant_types=["client_credentials"],
    )
    oauth2.set_o_auth2_client.side_effect = lambda **kwargs: HydraOAuth2Client(
        client_id=kwargs["id"],
        client_secret=kwargs["o_auth2_client"].client_secret,
        grant_types=["client_credentials"],
    )
    object.__setattr__(manager, "_client", sdk_client)
    object.__setattr__(manager, "_oauth2", oauth2)

    credentials = await manager.rotate_client_credentials("machine-client")

    assert credentials.client.client_id == "machine-client"
    assert len(credentials.client_secret) >= 64
    assert oauth2.set_o_auth2_client.call_args.kwargs["id"] == "machine-client"


@pytest.mark.unit
async def test_token_introspector_forwards_required_scopes() -> None:
    introspector = object.__new__(HydraTokenIntrospector)
    sdk_client = SimpleNamespace(
        timeout=10.0,
        call=AsyncMock(side_effect=lambda operation: operation()),
    )
    oauth2 = MagicMock()
    oauth2.introspect_o_auth2_token.return_value = cast(
        IntrospectedOAuth2Token,
        SimpleNamespace(active=True, client_id="machine-client", scope="orders:read"),
    )
    object.__setattr__(introspector, "_client", sdk_client)
    object.__setattr__(introspector, "_oauth2", oauth2)

    result = await introspector.introspect_access_token(
        "opaque-access-token",
        required_scopes=("orders:read",),
    )

    assert result.active is True
    oauth2.introspect_o_auth2_token.assert_called_once_with(
        token="opaque-access-token",
        scope="orders:read",
        _request_timeout=10.0,
    )
