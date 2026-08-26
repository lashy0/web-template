from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.audit.models import AuditEvent
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.audit.types import AuditActor, AuditEntity


@pytest.mark.unit
async def test_record_returns_event_created_by_repository() -> None:
    actor_id = uuid4()
    actor = AuditActor.user(
        actor_id,
        name="John",
        login="john",
    )

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

    service = AuditService(repository)

    result = await service.record(
        actor=actor,
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
async def test_record_supports_non_user_entity() -> None:
    expected = AuditEvent(
        actor_type="system",
        actor_id=None,
        actor_display_name=None,
        actor_identifier=None,
        action="project.updated",
        entity_type="project",
        entity_id="project-42",
        entity_display_name="New Project",
        entity_identifier="project-42",
        old_data={"name": "Old Project"},
        new_data={"name": "New Project"},
    )

    repository = AsyncMock(spec=AuditRepository)
    repository.create.return_value = expected

    service = AuditService(repository)

    result = await service.record(
        actor=AuditActor.system(),
        entity=AuditEntity(
            type="project",
            id="project-42",
            display_name="New Project",
            identifier="project-42",
        ),
        action="project.updated",
        old_data={"name": "Old Project"},
        new_data={"name": "New Project"},
    )

    assert result is expected

    repository.create.assert_awaited_once_with(
        actor_type="system",
        actor_id=None,
        actor_display_name=None,
        actor_identifier=None,
        action="project.updated",
        entity_type="project",
        entity_id="project-42",
        entity_display_name="New Project",
        entity_identifier="project-42",
        old_data={"name": "Old Project"},
        new_data={"name": "New Project"},
    )


@pytest.mark.unit
async def test_record_rejects_invalid_action_format() -> None:
    repository = AsyncMock(spec=AuditRepository)
    service = AuditService(repository)

    with pytest.raises(
        ValueError,
        match="Audit action must use",
    ):
        await service.record(
            actor=AuditActor.system(),
            entity=AuditEntity(type="user", id="user-42"),
            action="USER_UPDATED",
        )

    repository.create.assert_not_awaited()
