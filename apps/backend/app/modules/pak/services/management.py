"""Deprecated compatibility facade; new application code uses equipment commands directly."""

from uuid import UUID

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import OAuthClientManager, TokenIntrospector
from app.contexts.equipment.pak.authentication import PakMachineAuthenticator
from app.contexts.equipment.pak.commands import (
    CreatePak,
    DeletePak,
    GetPakAccessKey,
    RotatePakAccessKey,
    SetPakActive,
    SetPakArchived,
    UpdatePak,
)
from app.contexts.equipment.pak.model import PakDevice, PakDeviceKind
from app.contexts.equipment.pak.queries import PakQueries
from app.contexts.quality.verification.adapters import QualityPakVerificationHistoryAdapter
from app.infrastructure.hydra.pak import (
    HydraPakOAuthClientAdapter,
    HydraPakTokenIntrospectorAdapter,
)
from app.shared.security import CurrentPrincipal


class PakManagementService:
    """Compatibility delegation only; it owns no PAK workflow implementation."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        oauth_clients: OAuthClientManager,
        token_introspector: TokenIntrospector,
        access_key_encryption_key: SecretStr | None,
    ) -> None:
        oauth = HydraPakOAuthClientAdapter(oauth_clients)
        self._queries = PakQueries(session_factory)
        self._create = CreatePak(session_factory, oauth, access_key_encryption_key)
        self._update = UpdatePak(session_factory)
        self._active = SetPakActive(session_factory)
        self._archived = SetPakArchived(session_factory)
        self._delete = DeletePak(
            session_factory, oauth, QualityPakVerificationHistoryAdapter, access_key_encryption_key
        )
        self._access_key = GetPakAccessKey(session_factory, access_key_encryption_key)
        self._rotate = RotatePakAccessKey(session_factory, oauth, access_key_encryption_key)
        self._authentication = PakMachineAuthenticator(
            session_factory, HydraPakTokenIntrospectorAdapter(token_introspector)
        )

    async def get(self, pak_id: UUID) -> PakDevice | None:
        return await self._queries.get(pak_id)

    async def list(self, **kwargs: object) -> tuple[list[PakDevice], int]:
        return await self._queries.list(**kwargs)  # type: ignore[arg-type]

    async def create(
        self, *, actor: CurrentPrincipal, code: str, kind: PakDeviceKind, active: bool
    ) -> tuple[PakDevice, str]:
        return await self._create.execute(actor=actor, code=code, kind=kind, active=active)

    async def update(
        self, *, actor: CurrentPrincipal, pak_id: UUID, code: str | None, kind: PakDeviceKind | None
    ) -> PakDevice:
        return await self._update.execute(actor=actor, pak_id=pak_id, code=code, kind=kind)

    async def set_active(self, *, actor: CurrentPrincipal, pak_id: UUID, active: bool) -> PakDevice:
        return await self._active.execute(actor=actor, pak_id=pak_id, active=active)

    async def set_archived(
        self, *, actor: CurrentPrincipal, pak_id: UUID, archived: bool
    ) -> PakDevice:
        return await self._archived.execute(actor=actor, pak_id=pak_id, archived=archived)

    async def delete(self, *, actor: CurrentPrincipal, pak_id: UUID) -> None:
        await self._delete.execute(actor=actor, pak_id=pak_id)

    async def get_access_key(self, *, actor: CurrentPrincipal, pak_id: UUID) -> str:
        return await self._access_key.execute(actor=actor, pak_id=pak_id)

    async def rotate_access_key(self, *, actor: CurrentPrincipal, pak_id: UUID) -> str:
        return await self._rotate.execute(actor=actor, pak_id=pak_id)

    async def authorize_machine_access_token(self, access_token: str) -> PakDevice:
        return await self._authentication.authorize_machine_access_token(access_token)
