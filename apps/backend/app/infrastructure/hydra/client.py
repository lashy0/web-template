from collections.abc import Callable
from secrets import token_urlsafe
from typing import TypeVar

import anyio
import httpx2
import ory_hydra_client as hydra
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2.rfc6749.errors import OAuth2Error
from ory_hydra_client.api.o_auth2_api import OAuth2Api
from ory_hydra_client.exceptions import ApiException
from ory_hydra_client.models.introspected_o_auth2_token import IntrospectedOAuth2Token
from ory_hydra_client.models.o_auth2_client import OAuth2Client as HydraOAuth2Client

from app.auth.contracts import (
    AccessTokenIntrospection,
    OAuthAccessToken,
    OAuthClient,
    OAuthClientCredentials,
)
from app.auth.exceptions import (
    InvalidMachineCredentialsError,
    OAuthClientAlreadyExistsError,
    OAuthClientNotFoundError,
    OAuthProviderUnavailableError,
)
from app.core.config import Settings

T = TypeVar("T")
_CLIENT_SECRET_BYTES = 48


def _new_client_secret() -> str:
    return token_urlsafe(_CLIENT_SECRET_BYTES)


def _oauth_client(value: HydraOAuth2Client) -> OAuthClient:
    if value.client_id is None:
        raise OAuthProviderUnavailableError

    return OAuthClient(
        client_id=value.client_id,
        name=value.client_name,
        grant_types=tuple(value.grant_types or ()),
        scopes=tuple((value.scope or "").split()),
        token_endpoint_auth_method=value.token_endpoint_auth_method,
    )


def _credentials(value: HydraOAuth2Client) -> OAuthClientCredentials:
    if value.client_secret is None:
        raise OAuthProviderUnavailableError
    return OAuthClientCredentials(client=_oauth_client(value), client_secret=value.client_secret)


def _introspection(value: IntrospectedOAuth2Token) -> AccessTokenIntrospection:
    return AccessTokenIntrospection(
        active=value.active,
        client_id=value.client_id,
        scopes=tuple((value.scope or "").split()),
    )


class _SdkClient:
    def __init__(self, *, base_url: str, timeout: float, concurrency: int) -> None:
        configuration = hydra.Configuration(host=base_url.rstrip("/"), retries=0)
        self.api_client = hydra.ApiClient(configuration)
        self.timeout = timeout
        self.limiter = anyio.CapacityLimiter(concurrency)

    async def call(self, operation: Callable[[], T]) -> T:
        try:
            async with self.limiter:
                return await anyio.to_thread.run_sync(operation)

        except ApiException as exc:
            if exc.status == 404:
                raise OAuthClientNotFoundError from exc

            if exc.status == 409:
                raise OAuthClientAlreadyExistsError from exc

            raise OAuthProviderUnavailableError from exc

        except (OSError, TimeoutError) as exc:
            raise OAuthProviderUnavailableError from exc


class HydraOAuthClientManager:
    def __init__(self, settings: Settings) -> None:
        self._client = _SdkClient(
            base_url=settings.HYDRA_ADMIN_URL,
            timeout=settings.HYDRA_ADMIN_TIMEOUT,
            concurrency=settings.HYDRA_ADMIN_CONCURRENCY,
        )
        self._oauth2 = OAuth2Api(self._client.api_client)

    async def create_client(
        self,
        *,
        client_id: str | None = None,
        name: str | None = None,
        scopes: tuple[str, ...] = (),
    ) -> OAuthClientCredentials:
        client = HydraOAuth2Client(
            client_secret=_new_client_secret(),
            client_id=client_id,
            client_name=name,
            grant_types=["client_credentials"],
            response_types=[],
            scope=" ".join(scopes),
            token_endpoint_auth_method="client_secret_basic",
        )
        result = await self._client.call(
            lambda: self._oauth2.create_o_auth2_client(
                o_auth2_client=client,
                _request_timeout=self._client.timeout,
            )
        )

        return _credentials(result)

    async def get_client(self, client_id: str) -> OAuthClient:
        result = await self._client.call(
            lambda: self._oauth2.get_o_auth2_client(
                id=client_id,
                _request_timeout=self._client.timeout,
            )
        )

        return _oauth_client(result)

    async def delete_client(self, client_id: str) -> None:
        await self._client.call(
            lambda: self._oauth2.delete_o_auth2_client(
                id=client_id,
                _request_timeout=self._client.timeout,
            )
        )

    async def rotate_client_credentials(self, client_id: str) -> OAuthClientCredentials:
        current = await self._client.call(
            lambda: self._oauth2.get_o_auth2_client(
                id=client_id,
                _request_timeout=self._client.timeout,
            )
        )
        replacement_secret = _new_client_secret()
        replacement = current.model_copy(update={"client_secret": replacement_secret})
        result = await self._client.call(
            lambda: self._oauth2.set_o_auth2_client(
                id=client_id,
                o_auth2_client=replacement,
                _request_timeout=self._client.timeout,
            )
        )

        return _credentials(result)


class HydraTokenIntrospector:
    def __init__(self, settings: Settings) -> None:
        self._client = _SdkClient(
            base_url=settings.HYDRA_ADMIN_URL,
            timeout=settings.HYDRA_ADMIN_TIMEOUT,
            concurrency=settings.HYDRA_ADMIN_CONCURRENCY,
        )
        self._oauth2 = OAuth2Api(self._client.api_client)

    async def introspect_access_token(
        self,
        access_token: str,
        *,
        required_scopes: tuple[str, ...] = (),
    ) -> AccessTokenIntrospection:
        result = await self._client.call(
            lambda: self._oauth2.introspect_o_auth2_token(
                token=access_token,
                scope=" ".join(required_scopes) or None,
                _request_timeout=self._client.timeout,
            )
        )

        return _introspection(result)


class HydraMachineTokenIssuer:
    def __init__(self, settings: Settings) -> None:
        self._token_url = (
            f"{settings.HYDRA_PUBLIC_URL.rstrip('/')}/oauth2/token"
        )
        self._timeout = settings.HYDRA_PUBLIC_TIMEOUT

    async def issue_client_credentials_token(
        self,
        *,
        client_id: str,
        client_secret: str,
        scopes: tuple[str, ...] = (),
    ) -> OAuthAccessToken:
        try:
            async with AsyncOAuth2Client(
                client_id=client_id,
                client_secret=client_secret,
                scope=" ".join(scopes),
                timeout=self._timeout,
            ) as client:
                token = await client.fetch_token(
                    self._token_url,
                    grant_type="client_credentials",
                )

        except OAuth2Error as exc:
            raise InvalidMachineCredentialsError from exc

        except httpx2.HTTPError as exc:
            raise OAuthProviderUnavailableError from exc

        return OAuthAccessToken(
            access_token=token["access_token"],
            token_type=token.get("token_type", "Bearer"),
            expires_in=token["expires_in"],
            scopes=tuple(
                str(token.get("scope", "")).split()
            ),
        )
