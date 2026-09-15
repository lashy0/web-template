from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PakOAuthClient:
    client_id: str


@dataclass(frozen=True, slots=True)
class PakOAuthClientCredentials:
    client: PakOAuthClient
    client_secret: str


@dataclass(frozen=True, slots=True)
class PakTokenIntrospection:
    active: bool
    client_id: str | None


class PakOAuthClientPort(Protocol):
    async def create_client(
        self, *, client_id: str, client_secret: str | None = None
    ) -> PakOAuthClientCredentials: ...

    async def delete_client(self, client_id: str) -> None: ...

    async def rotate_client_credentials(self, client_id: str) -> PakOAuthClientCredentials: ...

    async def set_client_secret(
        self, client_id: str, client_secret: str
    ) -> PakOAuthClientCredentials: ...


class PakTokenIntrospectorPort(Protocol):
    async def introspect_access_token(self, access_token: str) -> PakTokenIntrospection: ...


class PakVerificationHistoryPort(Protocol):
    async def has_history_for_pak(self, pak_id: UUID) -> bool: ...
