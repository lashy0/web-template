from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        actor_type: str,
        actor_id: str | None = None,
        actor_display_name: str | None = None,
        actor_identifier: str | None = None,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        entity_display_name: str | None = None,
        entity_identifier: str | None = None,
        old_data: dict[str, Any] | None = None,
        new_data: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            actor_type=actor_type,
            actor_id=actor_id,
            actor_display_name=actor_display_name,
            actor_identifier=actor_identifier,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_display_name=entity_display_name,
            entity_identifier=entity_identifier,
            old_data=old_data,
            new_data=new_data,
        )

        self._session.add(event)

        await self._session.flush()
        await self._session.refresh(event)

        return event

    async def search(
        self,
        *,
        order: str,
        page: int,
        page_size: int,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        entity_type: str | None = None,
        sort: str,
    ) -> tuple[list[AuditEvent], int]:
        filters = [AuditEvent.entity_type == entity_type] if entity_type else []

        if created_from is not None:
            filters.append(AuditEvent.created_at >= created_from)

        if created_to is not None:
            filters.append(AuditEvent.created_at < created_to)

        column = {
            "created_at": AuditEvent.created_at,
            "actor_display_name": AuditEvent.actor_display_name,
        }[sort]

        sorted_column = (
            column.desc().nulls_last()
            if order == "desc"
            else column.asc().nulls_last()
        )

        statement = (
            select(AuditEvent)
            .where(*filters)
            .order_by(sorted_column, AuditEvent.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        count = await self._session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(*filters)
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all()), int(count or 0)
