from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class OAuthClient:
    client_id: str


@dataclass(frozen=True, slots=True)
class OAuthClientCredentials:
    client: OAuthClient
    client_secret: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class AccessTokenIntrospection:
    active: bool
    client_id: str | None
