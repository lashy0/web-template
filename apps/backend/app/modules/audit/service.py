import re
from typing import Any, Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent
from app.modules.audit.repository import AuditRepository
from app.modules.audit.types import AuditActor, AuditEntity

ACTION_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"
)


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self._repository = repository

    @classmethod
    def from_session(cls, session: AsyncSession) -> Self:
        return cls(AuditRepository(session))

    async def record(
        self,
        *,
        actor: AuditActor,
        entity: AuditEntity,
        action: str,
        old_data: dict[str, Any] | None = None,
        new_data: dict[str, Any] | None = None,
    ) -> AuditEvent:
        if not ACTION_PATTERN.fullmatch(action):
            raise ValueError(
                "Audit action must use '<namespace>.<operation>' format"
            )

        return await self._repository.create(
            actor_type=actor.type,
            actor_id=actor.id,
            actor_display_name=actor.display_name,
            actor_identifier=actor.identifier,
            action=action,
            entity_type=entity.type,
            entity_id=entity.id,
            entity_display_name=entity.display_name,
            entity_identifier=entity.identifier,
            old_data=old_data,
            new_data=new_data,
        )
