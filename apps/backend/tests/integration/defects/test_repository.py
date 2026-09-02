from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.defects.repository import DefectGroupRepository, DefectTypeRepository


@pytest.mark.integration
async def test_defect_groups_and_types_can_be_created_and_searched(
    db_session: AsyncSession,
) -> None:
    group_repository = DefectGroupRepository(db_session)
    type_repository = DefectTypeRepository(db_session)
    suffix = uuid4().hex[:8]
    group = await group_repository.create(
        code=f"POWER_{suffix}", name="Power supply", description="Power-related failures"
    )
    defect_type = await type_repository.create(
        group_id=group.id,
        code=f"VOLTAGE_LOW_{suffix}",
        name="Low voltage",
        description="Voltage is below the acceptable range.",
        possible_cause="Loose cable",
        engineer_action="Check the cable.",
    )

    groups, group_total = await group_repository.search(
        q="power", archived=False, page=1, page_size=25, sort="code", order="asc"
    )
    types, type_total = await type_repository.search(
        q="voltage",
        group_id=group.id,
        archived=False,
        page=1,
        page_size=25,
        sort="code",
        order="asc",
    )

    assert group_total == 1
    assert [item.id for item in groups] == [group.id]
    assert type_total == 1
    assert [item.id for item in types] == [defect_type.id]
    assert await type_repository.exists_by_group(group.id)
    assert await type_repository.exists_unarchived_by_group(group.id)


@pytest.mark.integration
async def test_archived_type_is_excluded_from_active_search_and_existence_check(
    db_session: AsyncSession,
) -> None:
    group_repository = DefectGroupRepository(db_session)
    type_repository = DefectTypeRepository(db_session)
    suffix = uuid4().hex[:8]
    group = await group_repository.create(code=f"MECH_{suffix}", name="Mechanical", description=None)
    defect_type = await type_repository.create(
        group_id=group.id,
        code=f"HOUSING_{suffix}",
        name="Damaged housing",
        description="Housing is damaged.",
        possible_cause=None,
        engineer_action=None,
    )
    await type_repository.update_archived(defect_type, archived_at=datetime.now(UTC))

    active, active_total = await type_repository.search(
        q=None,
        group_id=group.id,
        archived=False,
        page=1,
        page_size=25,
        sort="code",
        order="asc",
    )
    archived, archived_total = await type_repository.search(
        q=None,
        group_id=group.id,
        archived=True,
        page=1,
        page_size=25,
        sort="code",
        order="asc",
    )

    assert active == []
    assert active_total == 0
    assert archived_total == 1
    assert [item.id for item in archived] == [defect_type.id]
    assert not await type_repository.exists_unarchived_by_group(group.id)


@pytest.mark.integration
async def test_defect_group_and_type_codes_are_unique(db_session: AsyncSession) -> None:
    group_repository = DefectGroupRepository(db_session)
    type_repository = DefectTypeRepository(db_session)
    suffix = uuid4().hex[:8]
    group = await group_repository.create(code=f"UNIQUE_{suffix}", name="Unique", description=None)
    await type_repository.create(
        group_id=group.id,
        code=f"TYPE_{suffix}",
        name="First type",
        description="First description.",
        possible_cause=None,
        engineer_action=None,
    )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await group_repository.create(code=group.code, name="Duplicate", description=None)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await type_repository.create(
                group_id=group.id,
                code=f"TYPE_{suffix}",
                name="Duplicate type",
                description="Duplicate description.",
                possible_cause=None,
                engineer_action=None,
            )
