import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.audit.models import AuditEvent
from app.modules.audit.service import AuditService
from app.modules.defects.exceptions import (
    DefectGroupArchivedError,
    DefectGroupHasUnarchivedTypesError,
)
from app.modules.defects.models import DefectGroup, DefectType
from app.modules.defects.services import DefectManagementService

pytestmark = pytest.mark.integration


def actor():
    return CurrentPrincipal(
        user_id=uuid4(), identity_id=uuid4(), session_id=uuid4(), role=Role.ADMINISTRATOR
    )


@pytest.mark.parametrize("restore", [False, True])
async def test_group_archive_competes_with_type_create_or_restore(
    database_session_factory, restore
):
    factory = database_session_factory
    service = DefectManagementService(factory)
    principal = actor()
    group = await service.create_group(
        actor=principal, code=uuid4().hex, name="Group", description=None
    )
    arguments = {
        "actor": principal,
        "group_id": group.id,
        "code": uuid4().hex,
        "name": "Type",
        "description": "Description",
        "possible_cause": None,
        "engineer_action": None,
    }
    if restore:
        item = await service.create_type(**arguments)
        await service.set_type_archived(actor=principal, defect_type_id=item.id, archived=True)
        operation = service.set_type_archived(
            actor=principal, defect_type_id=item.id, archived=False
        )
    else:
        operation = service.create_type(**arguments)
    results = await asyncio.gather(
        service.set_group_archived(actor=principal, group_id=group.id, archived=True),
        operation,
        return_exceptions=True,
    )
    assert (
        sum(
            isinstance(r, (DefectGroupArchivedError, DefectGroupHasUnarchivedTypesError))
            for r in results
        )
        == 1
    )
    async with factory() as session:
        saved = await session.get(DefectGroup, group.id)
        active = await session.scalar(
            select(func.count())
            .select_from(DefectType)
            .where(DefectType.group_id == group.id, DefectType.archived_at.is_(None))
        )
        assert saved.archived_at is None or active == 0


async def test_group_update_rolls_back_when_audit_fails(database_session_factory, mocker):
    factory = database_session_factory
    service = DefectManagementService(factory)
    principal = actor()
    group = await service.create_group(
        actor=principal, code=uuid4().hex, name="Original", description=None
    )
    mocker.patch.object(AuditService, "record", side_effect=RuntimeError("audit unavailable"))
    with pytest.raises(RuntimeError, match="audit unavailable"):
        await service.update_group(actor=principal, group_id=group.id, updates={"name": "Changed"})
    assert (await service.get_group(group.id)).name == "Original"
    async with factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.entity_id == str(group.id))
            )
            == 1
        )
