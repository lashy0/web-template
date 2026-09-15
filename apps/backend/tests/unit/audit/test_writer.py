from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.audit.model import AuditEvent
from app.audit.repository import AuditRepository
from app.audit.types import AuditActor, AuditEntity
from app.audit.writer import TransactionalAuditWriter


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
async def test_writer_records_a_user_actor_and_returns_the_repository_event() -> None:
    actor_id = uuid4()
    expected = AuditEvent(
        actor_type="user",
        actor_id=str(actor_id),
        actor_display_name="John",
        actor_identifier="john",
        action="user.updated",
        entity_type="user",
        entity_id="user-42",
        entity_display_name="New Name",
        entity_identifier="new-name",
        old_data={"name": "Old Name"},
        new_data={"name": "New Name"},
    )

    repository = AsyncMock(spec=AuditRepository)
    repository.create.return_value = expected
    writer = TransactionalAuditWriter(repository)

    result = await writer.record(
        actor=AuditActor.user(actor_id, name="John", login="john"),
        entity=AuditEntity(
            type="user",
            id="user-42",
            display_name="New Name",
            identifier="new-name",
        ),
        action="user.updated",
        old_data={"name": "Old Name"},
        new_data={"name": "New Name"},
    )

    assert result is expected
    repository.create.assert_awaited_once_with(
        actor_type="user",
        actor_id=str(actor_id),
        actor_display_name="John",
        actor_identifier="john",
        action="user.updated",
        entity_type="user",
        entity_id="user-42",
        entity_display_name="New Name",
        entity_identifier="new-name",
        old_data={"name": "Old Name"},
        new_data={"name": "New Name"},
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
