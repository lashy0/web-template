from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import Role
from app.modules.audit.models import AuditEvent
from app.modules.audit.repository import AuditRepository
from app.modules.users.repository import UserRepository


@pytest.mark.integration
async def test_audit_event_preserves_snapshots_after_source_entities_change_or_are_deleted(
    db_session: AsyncSession,
) -> None:
    users = UserRepository(db_session)
    actor = await users.create(
        identity_id=uuid4(),
        name="Audit Actor",
        role=Role.ADMINISTRATOR,
    )
    target = await users.create(
        identity_id=uuid4(),
        name="Target User",
        role=Role.OPERATOR,
    )
    repository = AuditRepository(db_session)

    event = await repository.create(
        actor_type="user",
        actor_id=str(actor.id),
        actor_display_name="Audit Actor",
        actor_identifier="audit-actor",
        action="user.updated",
        entity_type="user",
        entity_id=str(target.id),
        entity_display_name="Target User",
        entity_identifier="target-user",
        old_data={"role": "operator"},
        new_data={"role": "manager"},
    )

    assert event.actor_type == "user"
    assert event.actor_id == str(actor.id)
    assert event.actor_display_name == "Audit Actor"
    assert event.actor_identifier == "audit-actor"
    assert event.action == "user.updated"
    assert event.entity_type == "user"
    assert event.entity_id == str(target.id)
    assert event.entity_display_name == "Target User"
    assert event.entity_identifier == "target-user"
    assert event.old_data == {"role": "operator"}
    assert event.new_data == {"role": "manager"}
    assert event.created_at.tzinfo is not None

    await users.update_name(actor, name="Changed Actor")
    await users.update_name(target, name="Changed Target")
    await users.delete(actor)
    await users.delete(target)

    events, total = await repository.search(
        entity_type="user",
        order="desc",
        page=1,
        page_size=25,
        sort="created_at",
    )

    assert events == [event]
    assert total == 1
    assert events[0].actor_display_name == "Audit Actor"
    assert events[0].actor_identifier == "audit-actor"
    assert events[0].entity_display_name == "Target User"
    assert events[0].entity_identifier == "target-user"


@pytest.mark.integration
async def test_audit_search_filters_by_an_exclusive_end_of_period(
    db_session: AsyncSession,
) -> None:
    repository = AuditRepository(db_session)
    outside_event = AuditEvent(
        actor_type="system",
        action="user.created",
        created_at=datetime(2026, 8, 17, 23, 59, tzinfo=UTC),
        entity_type="user",
    )
    period_event = AuditEvent(
        actor_type="system",
        action="user.created",
        created_at=datetime(2026, 8, 18, 12, tzinfo=UTC),
        entity_type="user",
    )
    end_event = AuditEvent(
        actor_type="system",
        action="user.created",
        created_at=datetime(2026, 8, 19, tzinfo=UTC),
        entity_type="user",
    )
    db_session.add_all([outside_event, period_event, end_event])
    await db_session.flush()

    events, total = await repository.search(
        created_from=datetime(2026, 8, 18, tzinfo=UTC),
        created_to=datetime(2026, 8, 19, tzinfo=UTC),
        entity_type="user",
        order="desc",
        page=1,
        page_size=25,
        sort="created_at",
    )

    assert events == [period_event]
    assert total == 1
