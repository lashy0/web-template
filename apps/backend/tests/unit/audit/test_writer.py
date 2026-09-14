from unittest.mock import AsyncMock

import pytest

from app.audit.writer import TransactionalAuditWriter
from app.modules.audit.repository import AuditRepository
from app.modules.audit.types import AuditActor, AuditEntity


@pytest.mark.unit
async def test_writer_uses_the_supplied_session_bound_repository() -> None:
    repository = AsyncMock(spec=AuditRepository)
    writer = TransactionalAuditWriter(repository)

    await writer.record(
        actor=AuditActor.system(),
        entity=AuditEntity(type="batch", id="batch-42"),
        action="batch.created",
    )

    repository.create.assert_awaited_once_with(
        actor_type="system",
        actor_id=None,
        actor_display_name=None,
        actor_identifier=None,
        action="batch.created",
        entity_type="batch",
        entity_id="batch-42",
        entity_display_name=None,
        entity_identifier=None,
        old_data=None,
        new_data=None,
    )


@pytest.mark.unit
async def test_writer_rejects_invalid_action_without_writing() -> None:
    repository = AsyncMock(spec=AuditRepository)
    writer = TransactionalAuditWriter(repository)

    with pytest.raises(ValueError, match="Audit action must use"):
        await writer.record(
            actor=AuditActor.system(),
            entity=AuditEntity(type="batch", id="batch-42"),
            action="batch-created",
        )

    repository.create.assert_not_awaited()
