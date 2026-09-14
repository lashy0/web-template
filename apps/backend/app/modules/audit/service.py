from typing import Any, Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import TransactionalAuditWriter
from app.modules.audit.models import AuditEvent
from app.modules.audit.repository import AuditRepository
from app.modules.audit.types import AuditActor, AuditEntity


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self._writer = TransactionalAuditWriter(repository)

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
        return await self._writer.record(
            actor=actor,
            entity=entity,
            action=action,
            old_data=old_data,
            new_data=new_data,
        )
