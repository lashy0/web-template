from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Identity:
    id: UUID
    login: str
    active: bool
    metadata: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class AuthSession:
    id: UUID
    identity: Identity
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class OAuthClient:
    client_id: str
    name: str | None
    grant_types: tuple[str, ...]
    scopes: tuple[str, ...]
    token_endpoint_auth_method: str | None


@dataclass(frozen=True, slots=True)
class OAuthClientCredentials:
    client: OAuthClient
    client_secret: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class AccessTokenIntrospection:
    active: bool
    client_id: str | None
    scopes: tuple[str, ...]


class SessionProvider(Protocol):
    async def get_session(
        self,
        *,
        cookie_header: str,
    ) -> AuthSession:
        """Resolve an active authentication session from a cookie header."""
        raise NotImplementedError

    async def revoke_all_sessions(
        self,
        identity_id: UUID,
    ) -> None:
        """Revoke all active sessions belonging to an identity."""
        raise NotImplementedError


class SessionVerifier(Protocol):
    async def verify_session(self, *, cookie_header: str) -> AuthSession:
        """Verify a browser session with the Kratos Public API."""
        raise NotImplementedError


class IdentityProvider(Protocol):
    async def create_identity(
        self,
        *,
        login: str,
    ) -> Identity:
        """Create a new identity."""
        raise NotImplementedError

    async def get_identity(
        self,
        identity_id: UUID,
    ) -> Identity:
        """Retrieve an identity by its provider identifier."""
        raise NotImplementedError

    async def disable_identity(
        self,
        identity_id: UUID,
    ) -> None:
        """Disable an identity."""
        raise NotImplementedError

    async def delete_identity(
        self,
        identity_id: UUID,
    ) -> None:
        """Delete an identity."""
        raise NotImplementedError


class IdentityManager(Protocol):
    async def create_identity(
        self,
        *,
        login: str,
        password: str,
        active: bool,
        user_id: UUID,
        provisioning_kind: Literal["standard", "bootstrap"] = "standard",
    ) -> Identity:
        """Provision a backend-owned provider identity."""
        raise NotImplementedError

    async def get_identity_by_external_id(self, user_id: UUID) -> Identity:
        """Retrieve a backend-owned identity by its immutable local user ID."""
        raise NotImplementedError

    async def get_identity(self, identity_id: UUID) -> Identity:
        """Retrieve an identity."""
        raise NotImplementedError

    async def update_login(self, identity_id: UUID, *, login: str) -> Identity:
        """Update the identity login without invalidating sessions."""
        raise NotImplementedError

    async def set_password(self, identity_id: UUID, *, password: str) -> None:
        """Replace the identity password credential."""
        raise NotImplementedError

    async def set_active(self, identity_id: UUID, *, active: bool) -> Identity:
        """Activate or deactivate the identity."""
        raise NotImplementedError

    async def revoke_all_sessions(self, identity_id: UUID) -> None:
        """Invalidate every session for an identity."""
        raise NotImplementedError

    async def delete_identity(self, identity_id: UUID) -> None:
        """Permanently delete an identity and its associated credentials."""
        raise NotImplementedError

    async def list_identities(self, *, page_size: int) -> list[Identity]:
        """List identities for reconciliation."""
        raise NotImplementedError


class OAuthClientManager(Protocol):
    async def create_client(
        self,
        *,
        client_id: str | None = None,
        name: str | None = None,
        scopes: tuple[str, ...] = (),
        client_secret: str | None = None,
    ) -> OAuthClientCredentials:
        """Create a confidential client for the client-credentials grant."""
        raise NotImplementedError

    async def get_client(self, client_id: str) -> OAuthClient:
        """Retrieve a client without exposing its secret."""
        raise NotImplementedError

    async def delete_client(self, client_id: str) -> None:
        """Delete a client and revoke its credentials."""
        raise NotImplementedError

    async def rotate_client_credentials(self, client_id: str) -> OAuthClientCredentials:
        """Replace a client's secret and return it exactly once."""
        raise NotImplementedError

    async def set_client_secret(
        self, client_id: str, client_secret: str
    ) -> OAuthClientCredentials:
        """Restore a known secret while compensating a failed local operation."""
        raise NotImplementedError


class TokenIntrospector(Protocol):
    async def introspect_access_token(
        self,
        access_token: str,
        *,
        required_scopes: tuple[str, ...] = (),
    ) -> AccessTokenIntrospection:
        """Return the active state and OAuth client data for an access token."""
        raise NotImplementedError
