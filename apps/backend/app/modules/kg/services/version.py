"""Compatibility facade for migrated production KG version use cases."""

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.kg.commands import (
    CreateVersion,
    DeleteVersion,
    SetVersionArchived,
    UpdateVersion,
)
from app.contexts.production.kg.model import KgVersion
from app.contexts.production.kg.queries import KgQueries
from app.contexts.production.kg.repository import KgRepository
from app.shared.security import CurrentPrincipal


class KgVersionService:
    """Legacy import path only; all behavior belongs to production/kg."""

    def __init__(self, session: AsyncSession) -> None:
        repository = KgRepository(session)
        audit = TransactionalAuditWriter.from_session(session)
        self._queries = KgQueries(repository)
        self._create = CreateVersion(repository, audit)
        self._update = UpdateVersion(repository, audit)
        self._delete = DeleteVersion(repository, audit)
        self._archive = SetVersionArchived(repository, audit)

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
        return await self._queries.list_versions(
            q=q,
            archived=archived,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def create(
        self, *, actor: CurrentPrincipal, code: str, name: str, description: str | None
    ) -> KgVersion:
        return await self._create.execute(
            actor=actor, code=code, name=name, description=description
        )

    async def update(
        self, *, actor: CurrentPrincipal, version_id: UUID, updates: Mapping[str, object]
    ) -> KgVersion:
        return await self._update.execute(actor=actor, version_id=version_id, updates=updates)

    async def set_archived(
        self, *, actor: CurrentPrincipal, version_id: UUID, archived: bool
    ) -> KgVersion:
        return await self._archive.execute(actor=actor, version_id=version_id, archived=archived)

    async def delete(self, *, actor: CurrentPrincipal, version_id: UUID) -> None:
        await self._delete.execute(actor=actor, version_id=version_id)
