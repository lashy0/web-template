from typing import Literal
from uuid import UUID

from app.domains.identity.users.contracts import UserIdentityProviderPort
from app.infrastructure.kratos.client import KratosIdentityManager
from app.shared.security import Identity


class KratosUserIdentityProvider(UserIdentityProviderPort):
    """Application-facing Kratos Admin adapter for user-management workflows."""

    def __init__(self, client: KratosIdentityManager) -> None:
        self._client = client

    async def create_identity(
        self,
        *,
        login: str,
        password: str,
        active: bool,
        user_id: UUID,
        provisioning_kind: Literal["standard", "bootstrap"] = "standard",
    ) -> Identity:
        return await self._client.create_identity(
            login=login,
            password=password,
            active=active,
            user_id=user_id,
            provisioning_kind=provisioning_kind,
        )

    async def get_identity_by_external_id(self, user_id: UUID) -> Identity:
        return await self._client.get_identity_by_external_id(user_id)

    async def get_identity(self, identity_id: UUID) -> Identity:
        return await self._client.get_identity(identity_id)

    async def update_login(self, identity_id: UUID, *, login: str) -> Identity:
        return await self._client.update_login(identity_id, login=login)

    async def set_password(self, identity_id: UUID, *, password: str) -> None:
        await self._client.set_password(identity_id, password=password)

    async def set_active(self, identity_id: UUID, *, active: bool) -> Identity:
        return await self._client.set_active(identity_id, active=active)

    async def revoke_all_sessions(self, identity_id: UUID) -> None:
        await self._client.revoke_all_sessions(identity_id)

    async def delete_identity(self, identity_id: UUID) -> None:
        await self._client.delete_identity(identity_id)

    async def list_identities(self, *, page_size: int) -> list[Identity]:
        return await self._client.list_identities(page_size=page_size)
