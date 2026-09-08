from __future__ import annotations

from uuid import UUID

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import OAuthClientManager, TokenIntrospector
from app.auth.principal import CurrentPrincipal

from ..enums import PakDeviceKind
from ..models import PakDevice
from .authentication import PakAuthenticationService
from .credentials import PakCredentialService
from .device import PakDeviceService
from .provisioning import PakProvisioningService


class PakManagementService:
    """Public compatibility gateway for the domain services."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        oauth_clients: OAuthClientManager,
        token_introspector: TokenIntrospector,
        access_key_encryption_key: SecretStr | None,
    ) -> None:
        self._device = PakDeviceService(session_factory)
        self._provisioning = PakProvisioningService(
            session_factory, oauth_clients, access_key_encryption_key
        )
        self._credentials = PakCredentialService(
            session_factory, oauth_clients, access_key_encryption_key
        )
        self._authentication = PakAuthenticationService(session_factory, token_introspector)

    async def get(self, pak_id: UUID) -> PakDevice | None:
        return await self._device.get(pak_id)

    async def list(
        self,
        *,
        q: str | None,
        kind: PakDeviceKind | None,
        active: bool | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[PakDevice], int]:
        return await self._device.list(
            q=q,
            kind=kind,
            active=active,
            archived=archived,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
        code: str | None,
        kind: PakDeviceKind | None,
    ) -> PakDevice:
        return await self._device.update(
            actor=actor,
            pak_id=pak_id,
            code=code,
            kind=kind,
        )

    async def set_active(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
        active: bool,
    ) -> PakDevice:
        return await self._device.set_active(
            actor=actor,
            pak_id=pak_id,
            active=active,
        )

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
        archived: bool,
    ) -> PakDevice:
        return await self._device.set_archived(
            actor=actor,
            pak_id=pak_id,
            archived=archived,
        )

    async def create(
        self,
        *,
        actor: CurrentPrincipal,
        code: str,
        kind: PakDeviceKind,
        active: bool,
    ) -> tuple[PakDevice, str]:
        return await self._provisioning.create(
            actor=actor,
            code=code,
            kind=kind,
            active=active,
        )

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
    ) -> None:
        return await self._provisioning.delete(
            actor=actor,
            pak_id=pak_id,
        )

    async def get_access_key(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
    ) -> str:
        return await self._credentials.get_access_key(
            actor=actor,
            pak_id=pak_id,
        )

    async def rotate_access_key(
        self,
        *,
        actor: CurrentPrincipal,
        pak_id: UUID,
    ) -> str:
        return await self._credentials.rotate_access_key(
            actor=actor,
            pak_id=pak_id,
        )

    async def authorize_machine_access_token(
        self,
        access_token: str,
    ) -> PakDevice:
        return await self._authentication.authorize_machine_access_token(
            access_token,
        )
