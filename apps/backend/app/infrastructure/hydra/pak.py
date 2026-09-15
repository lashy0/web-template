"""Hydra implementations of the narrow PAK outbound contracts."""

from app.auth.contracts import OAuthClientManager, TokenIntrospector
from app.auth.exceptions import OAuthClientNotFoundError
from app.domains.equipment.pak.contracts import (
    PakOAuthClient,
    PakOAuthClientCredentials,
    PakOAuthClientPort,
    PakTokenIntrospection,
    PakTokenIntrospectorPort,
)
from app.domains.equipment.pak.exceptions import PakOAuthClientNotFoundError


class HydraPakOAuthClientAdapter(PakOAuthClientPort):
    def __init__(self, clients: OAuthClientManager) -> None:
        self._clients = clients

    async def create_client(
        self, *, client_id: str, client_secret: str | None = None
    ) -> PakOAuthClientCredentials:
        result = await self._clients.create_client(client_id=client_id, client_secret=client_secret)
        return PakOAuthClientCredentials(
            client=PakOAuthClient(client_id=result.client.client_id),
            client_secret=result.client_secret,
        )

    async def delete_client(self, client_id: str) -> None:
        try:
            await self._clients.delete_client(client_id)
        except OAuthClientNotFoundError as exc:
            raise PakOAuthClientNotFoundError from exc

    async def rotate_client_credentials(self, client_id: str) -> PakOAuthClientCredentials:
        result = await self._clients.rotate_client_credentials(client_id)
        return PakOAuthClientCredentials(
            client=PakOAuthClient(client_id=result.client.client_id),
            client_secret=result.client_secret,
        )

    async def set_client_secret(
        self, client_id: str, client_secret: str
    ) -> PakOAuthClientCredentials:
        result = await self._clients.set_client_secret(client_id, client_secret)
        return PakOAuthClientCredentials(
            client=PakOAuthClient(client_id=result.client.client_id),
            client_secret=result.client_secret,
        )


class HydraPakTokenIntrospectorAdapter(PakTokenIntrospectorPort):
    def __init__(self, introspector: TokenIntrospector) -> None:
        self._introspector = introspector

    async def introspect_access_token(self, access_token: str) -> PakTokenIntrospection:
        result = await self._introspector.introspect_access_token(access_token)
        return PakTokenIntrospection(active=result.active, client_id=result.client_id)
