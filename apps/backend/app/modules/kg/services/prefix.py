from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService
from app.modules.batch.repositories import BatchRepository

from ..exceptions import (
    KgDevEuiPrefixArchivedError,
    KgDevEuiPrefixConflictError,
    KgDevEuiPrefixInUseError,
    KgDevEuiPrefixNotFoundError,
    KgDevEuiRangeOverflowError,
)
from ..models import KgDevEuiPrefix
from ..repositories import KgDevEuiPrefixRepository, KgRepository
from . import audit


class KgPrefixService:
    """Prefix CRUD and range allocation in a caller-owned transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._prefixes = KgDevEuiPrefixRepository(session)
        self._repository = KgRepository(session)

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
        return await self._prefixes.search(
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
        session = self._session
        repository = KgDevEuiPrefixRepository(session)

        if await repository.get(prefix) is not None:
            raise KgDevEuiPrefixConflictError

        if await repository.get_by_short_code(short_code) is not None:
            raise KgDevEuiPrefixConflictError

        try:
            item = await repository.create(
                prefix=prefix,
                short_code=short_code,
                name=name,
            )

        except IntegrityError as exc:
            raise KgDevEuiPrefixConflictError from exc

        await AuditService.from_session(session).record(
            actor=audit.actor_identity(actor),
            action="kg_prefix.created",
            entity=audit.prefix_entity(item),
            new_data={
                "prefix": item.prefix,
                "short_code": item.short_code,
                "name": item.name,
            },
        )

        return item

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
        updates: Mapping[str, object],
    ) -> KgDevEuiPrefix:
        session = self._session
        repository = KgDevEuiPrefixRepository(session)

        item = await self._required(repository, prefix)

        if not updates:
            return item

        old_values = {field: getattr(item, field) for field in updates}

        item = await repository.update_details(
            item,
            updates=updates,
        )

        new_values = {field: getattr(item, field) for field in updates}

        changed = {
            field: value for field, value in new_values.items() if value != old_values[field]
        }

        if changed:
            await AuditService.from_session(session).record(
                actor=audit.actor_identity(actor),
                action="kg_prefix.updated",
                entity=audit.prefix_entity(item),
                old_data={field: old_values[field] for field in changed},
                new_data=changed,
            )

        return item

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
    ) -> None:
        session = self._session
        repository = KgDevEuiPrefixRepository(session)

        await self._repository.lock_dev_eui_allocation(prefix)
        item = await self._required(repository, prefix)

        in_use = await BatchRepository(session).exists_by_dev_eui_prefix(item.prefix)

        if in_use:
            raise KgDevEuiPrefixInUseError

        await AuditService.from_session(session).record(
            actor=audit.actor_identity(actor),
            action="kg_prefix.deleted",
            entity=audit.prefix_entity(item),
            old_data={
                "prefix": item.prefix,
                "short_code": item.short_code,
                "name": item.name,
            },
        )

        await repository.delete(item)

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        prefix: str,
        archived: bool,
    ) -> KgDevEuiPrefix:
        item = await self._required(self._prefixes, prefix)

        if archived == (item.archived_at is not None):
            return item

        archived_at = datetime.now(UTC) if archived else None
        item = await self._prefixes.update_archived(item, archived_at=archived_at)

        await AuditService.from_session(self._session).record(
            actor=audit.actor_identity(actor),
            action="kg_prefix.archived" if archived else "kg_prefix.restored",
            entity=audit.prefix_entity(item),
        )

        return item

    @staticmethod
    async def _required(
        repository: KgDevEuiPrefixRepository,
        prefix: str,
    ) -> KgDevEuiPrefix:
        item = await repository.get(prefix, for_update=True)

        if item is None:
            raise KgDevEuiPrefixNotFoundError

        return item

    async def prepare_allocation(
        self,
        prefix: str,
        quantity: int,
    ) -> tuple[KgDevEuiPrefix, list[str]]:
        await self._repository.lock_dev_eui_allocation(prefix)
        item, start, end = await self._allocation_bounds(prefix, quantity)

        return item, [f"{item.prefix}{value:06x}" for value in range(start, end + 1)]

    async def preview_allocation(
        self,
        prefix: str,
        quantity: int,
    ) -> tuple[str, str]:
        item, start, end = await self._allocation_bounds(prefix, quantity)

        return f"{item.prefix}{start:06x}", f"{item.prefix}{end:06x}"

    async def _allocation_bounds(
        self,
        prefix: str,
        quantity: int,
    ) -> tuple[KgDevEuiPrefix, int, int]:
        item = await self._prefixes.get(prefix)

        if item is None:
            raise KgDevEuiPrefixNotFoundError

        if item.archived_at is not None:
            raise KgDevEuiPrefixArchivedError

        maximum = await self._repository.get_max_dev_eui_by_prefix(item.prefix)
        start = int(maximum[-6:], 16) + 1 if maximum else 1
        end = start + quantity - 1

        if end > 0xFFFFFF:
            raise KgDevEuiRangeOverflowError

        return item, start, end
