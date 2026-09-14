"""Compatibility facade for the migrated production KG use cases."""

from builtins import list as builtin_list
from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter
from app.contexts.production.kg.commands import (
    AllocateForBatch,
    CreatePrefix,
    DeletePrefix,
    SetPrefixArchived,
    UpdatePrefix,
)
from app.contexts.production.kg.model import KgDevEuiPrefix
from app.contexts.production.kg.queries import KgQueries
from app.contexts.production.kg.repository import KgRepository
from app.shared.security import CurrentPrincipal


class KgPrefixService:
    """Legacy import path only; all behavior belongs to production/kg."""

    def __init__(self, session: AsyncSession) -> None:
        repository = KgRepository(session)
        audit = TransactionalAuditWriter.from_session(session)
        self._queries = KgQueries(repository)
        self._create = CreatePrefix(repository, audit)
        self._update = UpdatePrefix(repository, audit)
        self._delete = DeletePrefix(repository, audit)
        self._archive = SetPrefixArchived(repository, audit)
        self._allocate = AllocateForBatch(repository)

    async def list(
        self, *, q: str | None, archived: bool, page: int, page_size: int, sort: str, order: str
    ) -> tuple[builtin_list[tuple[KgDevEuiPrefix, int]], int]:
        return await self._queries.list_prefixes(
            q=q, archived=archived, page=page, page_size=page_size, sort=sort, order=order
        )

    async def create(
        self, *, actor: CurrentPrincipal, prefix: str, short_code: str, name: str | None
    ) -> KgDevEuiPrefix:
        return await self._create.execute(
            actor=actor, prefix=prefix, short_code=short_code, name=name
        )

    async def update(
        self, *, actor: CurrentPrincipal, prefix: str, updates: Mapping[str, object]
    ) -> KgDevEuiPrefix:
        return await self._update.execute(actor=actor, prefix=prefix, updates=updates)

    async def delete(self, *, actor: CurrentPrincipal, prefix: str) -> None:
        await self._delete.execute(actor=actor, prefix=prefix)

    async def set_archived(
        self, *, actor: CurrentPrincipal, prefix: str, archived: bool
    ) -> KgDevEuiPrefix:
        return await self._archive.execute(actor=actor, prefix=prefix, archived=archived)

    async def prepare_allocation(
        self, prefix: str, quantity: int
    ) -> tuple[KgDevEuiPrefix, builtin_list[str]]:
        allocation = await self._allocate.execute(prefix=prefix, quantity=quantity)
        return allocation.prefix, allocation.dev_euis

    async def preview_allocation(self, prefix: str, quantity: int) -> tuple[str, str]:
        return await self._queries.preview_allocation(prefix, quantity)
