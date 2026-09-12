from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal

from ..models import KgDevEuiPrefix, KgState, KgUnit, KgVersion
from ..repositories import KgDevEuiPrefixRepository, KgVersionRepository
from ..repositories.unit import KgListItem
from ..schemas.state import KgCurrentState
from ..schemas.unit import KgBatchListItem
from .prefix import KgPrefixService as KgPrefixService
from .transactions import transaction
from .unit import KgService as KgService
from .version import KgVersionService


class KgManagementService:
    """API gateway owning sessions and transactions; delegates domain operations."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get_with_current_state(self, dev_eui: str) -> KgListItem | None:
        async with self._session_factory() as session:
            return await KgService(session).get_with_current_state(dev_eui)

    async def list(
        self,
        *,
        q: str | None,
        batch_id: UUID | None,
        current_state: KgCurrentState | None,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[KgListItem], int]:
        async with self._session_factory() as session:
            return await KgService(session).list(
                q=q,
                batch_id=batch_id,
                current_state=current_state,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )

    async def list_batch_items(
        self,
        batch_id: UUID,
        *,
        page: int,
        page_size: int,
        q: str | None,
        current_state: KgCurrentState | None,
    ) -> tuple[list[KgBatchListItem], int]:
        async with self._session_factory() as session:
            return await KgService(session).list_batch_items(
                batch_id,
                page=page,
                page_size=page_size,
                q=q,
                current_state=current_state,
            )

    async def set_state(
        self,
        *,
        actor: CurrentPrincipal,
        dev_eui: str,
        state: KgState,
    ) -> KgUnit:
        async with transaction(self._session_factory) as session:
            return await KgService(
                session,
            ).set_state(
                actor=actor,
                dev_eui=dev_eui,
                state=state,
            )

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        dev_eui: str,
    ) -> None:
        async with transaction(self._session_factory) as session:
            return await KgService(session).delete(
                actor=actor,
                dev_eui=dev_eui,
            )


class KgDevEuiPrefixManagementService:
    """API gateway owning sessions and transactions; delegates domain operations."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def list(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> tuple[list[tuple[KgDevEuiPrefix, int]], int]:
        async with self._session_factory() as session:
            return await KgPrefixService(session).list(
                q=q,
                archived=archived,
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
            )

    async def create(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
        short_code: str,
        name: str | None,
    ) -> KgDevEuiPrefix:
        async with transaction(self._session_factory) as session:
            return await KgPrefixService(session).create(
                actor=actor,
                prefix=prefix,
                short_code=short_code,
                name=name,
            )

    async def count_batches(self, prefix: str) -> int:
        async with self._session_factory() as session:
            return await KgDevEuiPrefixRepository(session).count_batches(prefix)

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
        updates: Mapping[str, object],
    ) -> KgDevEuiPrefix:
        async with transaction(self._session_factory) as session:
            return await KgPrefixService(session).update(
                actor=actor,
                prefix=prefix,
                updates=updates,
            )

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
    ) -> None:
        async with transaction(self._session_factory) as session:
            return await KgPrefixService(session).delete(actor=actor, prefix=prefix)

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
        archived: bool,
    ) -> KgDevEuiPrefix:
        async with transaction(self._session_factory) as session:
            return await KgPrefixService(session).set_archived(
                actor=actor,
                prefix=prefix,
                archived=archived,
            )


class KgVersionManagementService:
    """API gateway owning sessions and transactions for KG versions."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def list(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple[KgVersion, int]], int]:
        async with self._session_factory() as session:
            return await KgVersionService(session).list(
                q=q,
                archived=archived,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order,
            )

    async def create(
        self,
        *,
        actor: CurrentPrincipal,
        code: str,
        name: str,
        description: str | None,
    ) -> KgVersion:
        async with transaction(self._session_factory) as session:
            return await KgVersionService(session).create(
                actor=actor,
                code=code,
                name=name,
                description=description,
            )

    async def count_batches(self, version_id: UUID) -> int:
        async with self._session_factory() as session:
            return await KgVersionRepository(session).count_batches(version_id)

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        version_id: UUID,
        updates: Mapping[str, object],
    ) -> KgVersion:
        async with transaction(self._session_factory) as session:
            return await KgVersionService(session).update(
                actor=actor,
                version_id=version_id,
                updates=updates,
            )

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        version_id: UUID,
        archived: bool,
    ) -> KgVersion:
        async with transaction(self._session_factory) as session:
            return await KgVersionService(session).set_archived(
                actor=actor,
                version_id=version_id,
                archived=archived,
            )

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        version_id: UUID,
    ) -> None:
        async with transaction(self._session_factory) as session:
            await KgVersionService(session).delete(actor=actor, version_id=version_id)
