from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.modules.defects.exceptions import (
    DefectGroupArchivedError,
    DefectGroupHasUnarchivedTypesError,
)
from app.modules.defects.models import DefectGroup, DefectType
from app.modules.defects.service import DefectManagementService


class _Session:
    def begin(self) -> _Session:
        return self

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class _SessionFactory:
    def __call__(self) -> _Session:
        return _Session()


def _principal() -> CurrentPrincipal:
    return CurrentPrincipal(
        user_id=uuid4(),
        identity_id=uuid4(),
        session_id=uuid4(),
        role=Role.MANAGER,
        name="Manager",
        login="manager",
    )


def _group(*, archived_at: datetime | None = None) -> DefectGroup:
    now = datetime.now(UTC)
    return DefectGroup(
        id=uuid4(),
        code="POWER",
        name="Power supply",
        description="Power-related failures",
        archived_at=archived_at,
        created_at=now,
        updated_at=now,
    )


def _type(group: DefectGroup, *, archived_at: datetime | None = None) -> DefectType:
    now = datetime.now(UTC)
    return DefectType(
        id=uuid4(),
        group_id=group.id,
        code="VOLTAGE_LOW",
        name="Low voltage",
        description="Voltage is below the acceptable range.",
        possible_cause="Loose cable",
        engineer_action="Check the cable.",
        archived_at=archived_at,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def dependencies(mocker: MockerFixture) -> tuple[MagicMock, MagicMock, MagicMock]:
    groups = mocker.patch("app.modules.defects.service.DefectGroupRepository")
    groups.return_value.get_by_id = AsyncMock()
    groups.return_value.get_by_code = AsyncMock()
    groups.return_value.create = AsyncMock()
    groups.return_value.update_details = AsyncMock()
    groups.return_value.update_archived = AsyncMock()
    groups.return_value.delete = AsyncMock()
    defect_types = mocker.patch("app.modules.defects.service.DefectTypeRepository")
    defect_types.return_value.get_by_id = AsyncMock()
    defect_types.return_value.get_by_code = AsyncMock()
    defect_types.return_value.create = AsyncMock()
    defect_types.return_value.update_details = AsyncMock()
    defect_types.return_value.update_archived = AsyncMock()
    defect_types.return_value.delete = AsyncMock()
    defect_types.return_value.exists_by_group = AsyncMock(return_value=False)
    defect_types.return_value.exists_unarchived_by_group = AsyncMock(return_value=False)
    audits = mocker.patch("app.modules.defects.service.AuditService")
    audits.from_session.return_value.record = AsyncMock()
    return groups, defect_types, audits


def _service() -> DefectManagementService:
    return DefectManagementService(cast(async_sessionmaker[AsyncSession], _SessionFactory()))


@pytest.mark.unit
async def test_create_group_records_audit_event(
    dependencies: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    groups, _, audits = dependencies
    group = _group()
    groups.return_value.get_by_code.return_value = None
    groups.return_value.create.return_value = group

    created = await _service().create_group(
        actor=_principal(), code=group.code, name=group.name, description=group.description
    )

    assert created is group
    groups.return_value.create.assert_awaited_once_with(
        code="POWER", name="Power supply", description="Power-related failures"
    )
    record = audits.from_session.return_value.record.await_args.kwargs
    assert record["action"] == "defect_group.created"
    assert record["new_data"] == {
        "code": "POWER",
        "name": "Power supply",
        "description": "Power-related failures",
    }


@pytest.mark.unit
async def test_archiving_group_requires_all_its_types_to_be_archived(
    dependencies: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    groups, defect_types, audits = dependencies
    group = _group()
    groups.return_value.get_by_id.return_value = group
    defect_types.return_value.exists_unarchived_by_group.return_value = True

    with pytest.raises(DefectGroupHasUnarchivedTypesError):
        await _service().set_group_archived(actor=_principal(), group_id=group.id, archived=True)

    groups.return_value.update_archived.assert_not_awaited()
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_create_type_rejects_archived_group(
    dependencies: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    groups, defect_types, audits = dependencies
    group = _group(archived_at=datetime.now(UTC))
    groups.return_value.get_by_id.return_value = group

    with pytest.raises(DefectGroupArchivedError):
        await _service().create_type(
            actor=_principal(),
            group_id=group.id,
            code="VOLTAGE_LOW",
            name="Low voltage",
            description="Voltage is below the acceptable range.",
            possible_cause=None,
            engineer_action=None,
        )

    defect_types.return_value.create.assert_not_awaited()
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_restoring_type_rejects_archived_group(
    dependencies: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    groups, defect_types, audits = dependencies
    group = _group(archived_at=datetime.now(UTC))
    defect_type = _type(group, archived_at=datetime.now(UTC))
    groups.return_value.get_by_id.return_value = group
    defect_types.return_value.get_by_id.return_value = defect_type

    with pytest.raises(DefectGroupArchivedError):
        await _service().set_type_archived(
            actor=_principal(), defect_type_id=defect_type.id, archived=False
        )

    defect_types.return_value.update_archived.assert_not_awaited()
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_update_type_audits_only_changed_fields(
    dependencies: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    _, defect_types, audits = dependencies
    group = _group()
    defect_type = _type(group)
    defect_types.return_value.get_by_id.return_value = defect_type

    async def update_details(item: DefectType, *, updates: dict[str, object]) -> DefectType:
        for field, value in updates.items():
            setattr(item, field, value)
        return item

    defect_types.return_value.update_details.side_effect = update_details

    updated = await _service().update_type(
        actor=_principal(),
        defect_type_id=defect_type.id,
        updates={"name": "Low input voltage", "description": defect_type.description},
    )

    assert updated.name == "Low input voltage"
    record = audits.from_session.return_value.record.await_args.kwargs
    assert record["action"] == "defect_type.updated"
    assert record["old_data"] == {"name": "Low voltage"}
    assert record["new_data"] == {"name": "Low input voltage"}
