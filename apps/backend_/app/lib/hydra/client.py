from __future__ import annotations

from collections.abc import Callable
from secrets import token_urlsafe
from typing import TypeVar, cast

import anyio
import ory_hydra_client as hydra
from anyio.to_thread import run_sync
from ory_hydra_client.api.metadata_api import MetadataApi
from ory_hydra_client.api.o_auth2_api import OAuth2Api
from ory_hydra_client.exceptions import ApiException
from ory_hydra_client.models.introspected_o_auth2_token import IntrospectedOAuth2Token
from ory_hydra_client.models.o_auth2_client import OAuth2Client as HydraOAuth2Client

from app.lib.hydra.exceptions import (
    HydraClientAlreadyExistsError,
    HydraClientNotFoundError,
    HydraUnavailableError,
)
from app.lib.hydra.schemas import AccessTokenIntrospection, OAuthClient, OAuthClientCredentials

T = TypeVar("T")
_CLIENT_SECRET_BYTES = 48


def _new_client_secret() -> str:
    return token_urlsafe(_CLIENT_SECRET_BYTES)


def _oauth_client(value: HydraOAuth2Client) -> OAuthClient:
    if value.client_id is None:
        raise HydraUnavailableError(detail="Hydra returned an OAuth client without an ID.")

    return OAuthClient(client_id=value.client_id)


def _credentials(value: HydraOAuth2Client) -> OAuthClientCredentials:
    if value.client_secret is None:
        raise HydraUnavailableError(detail="Hydra did not return an OAuth client secret.")

    return OAuthClientCredentials(
        client=_oauth_client(value),
        client_secret=value.client_secret,
    )


def _introspection(value: IntrospectedOAuth2Token) -> AccessTokenIntrospection:
    return AccessTokenIntrospection(
        active=bool(value.active),
        client_id=value.client_id,
    )


class _SDKClient:
    """Run synchronous generated SDK calls without blocking the event loop."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float,
        concurrency: int,
    ) -> None:
        configuration = hydra.Configuration(
            host=base_url.rstrip("/"),
            retries=0,
        )

        self.api_client = hydra.ApiClient(configuration)
        self.timeout = timeout
        self.limiter = anyio.CapacityLimiter(concurrency)

    async def call(self, operation: Callable[[], T]) -> T:
        try:
            async with self.limiter:
                return await run_sync(operation)

        except ApiException as exc:
            status = cast("int | None", exc.status)

            if status == 404:
                raise HydraClientNotFoundError(
                    detail="Hydra OAuth client was not found.",
                ) from exc

            if status == 409:
                raise HydraClientAlreadyExistsError(
                    detail="Hydra OAuth client already exists.",
                ) from exc

            raise HydraUnavailableError(
                detail="Hydra request failed.",
            ) from exc

        except (OSError, TimeoutError) as exc:
            raise HydraUnavailableError(
                detail="Hydra request failed.",
            ) from exc

        except Exception as exc:
            raise HydraUnavailableError(
                detail="Hydra request failed.",
            ) from exc


class HydraClient:
    """Manage PAK OAuth clients and introspect their access tokens."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 10.0,
        concurrency: int = 4,
    ) -> None:
        client = _SDKClient(
            base_url=base_url,
            timeout=timeout,
            concurrency=concurrency,
        )

        self._client = client
        self._metadata = MetadataApi(client.api_client)
        self._oauth2 = OAuth2Api(client.api_client)

    async def is_ready(self) -> bool:
        """Return whether Hydra's Admin API is reachable."""
        try:
            await self._client.call(
                lambda: self._metadata.is_ready(
                    _request_timeout=self._client.timeout,
                )
            )
        except HydraUnavailableError:
            return False

        return True

    async def create_client(
        self,
        *,
        client_id: str,
        client_secret: str | None = None,
    ) -> OAuthClientCredentials:
        """Create a confidential client-credentials OAuth client."""
        client = HydraOAuth2Client(
            client_id=client_id,
            client_secret=client_secret or _new_client_secret(),
            grant_types=["client_credentials"],
            response_types=[],
            token_endpoint_auth_method="client_secret_basic",
        )
        result = await self._client.call(
            lambda: self._oauth2.create_o_auth2_client(
                o_auth2_client=client,
                _request_timeout=self._client.timeout,
            )
        )

        return _credentials(result)

    async def delete_client(self, client_id: str) -> None:
        """Delete an OAuth client and revoke its credentials; a missing client is not an error."""
        try:
            await self._client.call(
                lambda: self._oauth2.delete_o_auth2_client(
                    id=client_id,
                    _request_timeout=self._client.timeout,
                )
            )
        except HydraClientNotFoundError:
            # Makes post-commit deletion and rollback cleanup idempotent.
            return

    async def revoke_client_tokens(self, client_id: str) -> None:
        """Revoke all access tokens issued to an OAuth client."""
        await self._client.call(
            lambda: self._oauth2.delete_o_auth2_token(
                client_id=client_id,
                _request_timeout=self._client.timeout,
            )
        )

    async def get_client(self, client_id: str) -> OAuthClient:
        """Retrieve an OAuth client without exposing its secret."""
        result = await self._client.call(
            lambda: self._oauth2.get_o_auth2_client(
                id=client_id,
                _request_timeout=self._client.timeout,
            )
        )

        return _oauth_client(result)

    async def rotate_client_credentials(self, client_id: str) -> OAuthClientCredentials:
        """Rotate a client secret and return the replacement once."""
        return await self.set_client_secret(client_id, _new_client_secret())

    async def set_client_secret(
        self,
        client_id: str,
        client_secret: str,
    ) -> OAuthClientCredentials:
        """Set a known client secret, including for compensation."""
        current = await self._client.call(
            lambda: self._oauth2.get_o_auth2_client(
                id=client_id,
                _request_timeout=self._client.timeout,
            )
        )
        result = await self._client.call(
            lambda: self._oauth2.set_o_auth2_client(
                id=client_id,
                o_auth2_client=current.model_copy(update={"client_secret": client_secret}),
                _request_timeout=self._client.timeout,
            )
        )

        return _credentials(result)

    async def introspect_access_token(self, access_token: str) -> AccessTokenIntrospection:
        """Return token activity and the OAuth client that obtained it."""
        result = await self._client.call(
            lambda: self._oauth2.introspect_o_auth2_token(
                token=access_token,
                _request_timeout=self._client.timeout,
            )
        )

        return _introspection(result)
