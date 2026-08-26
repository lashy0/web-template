from dataclasses import dataclass
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
