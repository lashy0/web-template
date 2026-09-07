from __future__ import annotations

import builtins
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import CurrentPrincipal
from app.modules.audit.service import AuditService
from app.modules.batch.repositories import BatchRepository

from ..exceptions import (
    KgVersionConflictError,
    KgVersionInUseError,
    KgVersionNotFoundError,
)
from ..models import KgVersion
from ..repositories import KgVersionRepository
from . import audit


class KgVersionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = KgVersionRepository(session)

    async def list(
        self,
        *,
        q: str | None,
        archived: bool,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[builtins.list[KgVersion], int]:
        return await self._repository.search(
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
        if await self._repository.get_by_code(code) is not None:
            raise KgVersionConflictError

        try:
            item = await self._repository.create(
                code=code,
                name=name,
                description=description,
            )

        except IntegrityError as exc:
            raise KgVersionConflictError from exc

        await AuditService.from_session(self._session).record(
            actor=audit.actor_identity(actor),
            action="kg_version.created",
            entity=audit.version_entity(item),
            new_data={
                "code": item.code,
                "name": item.name,
                "description": item.description,
            },
        )

        return item

    async def update(
        self,
        *,
        actor: CurrentPrincipal,
        version_id: UUID,
        updates: Mapping[str, object],
    ) -> KgVersion:
        item = await self._required(version_id)

        if not updates:
            return item

        old_values = {field: getattr(item, field) for field in updates}
        item = await self._repository.update_details(item, updates=updates)
        changed = {
            field: getattr(item, field)
            for field, old_value in old_values.items()
            if getattr(item, field) != old_value
        }

        if changed:
            await AuditService.from_session(self._session).record(
                actor=audit.actor_identity(actor),
                action="kg_version.updated",
                entity=audit.version_entity(item),
                old_data={field: old_values[field] for field in changed},
                new_data=changed,
            )

        return item

    async def set_archived(
        self,
        *,
        actor: CurrentPrincipal,
        version_id: UUID,
        archived: bool,
    ) -> KgVersion:
        item = await self._required(version_id)

        if archived == (item.archived_at is not None):
            return item

        old_archived_at = item.archived_at
        item = await self._repository.update_archived(
            item,
            archived_at=datetime.now(UTC) if archived else None,
        )

        await AuditService.from_session(self._session).record(
            actor=audit.actor_identity(actor),
            action="kg_version.archived" if archived else "kg_version.restored",
            entity=audit.version_entity(item),
            old_data={
                "archived_at": old_archived_at.isoformat() if old_archived_at else None,
            },
            new_data={
                "archived_at": item.archived_at.isoformat() if item.archived_at else None,
            },
        )

        return item

    async def delete(
        self,
        *,
        actor: CurrentPrincipal,
        version_id: UUID,
    ) -> None:
        item = await self._required(version_id)

        if await BatchRepository(self._session).exists_by_kg_version_id(item.id):
            raise KgVersionInUseError

        await AuditService.from_session(self._session).record(
            actor=audit.actor_identity(actor),
            action="kg_version.deleted",
            entity=audit.version_entity(item),
            old_data={
                "code": item.code,
                "name": item.name,
                "description": item.description,
            },
        )

        await self._repository.delete(item)

    async def _required(self, version_id: UUID) -> KgVersion:
        item = await self._repository.get(version_id, for_update=True)

        if item is None:
            raise KgVersionNotFoundError

        return item
