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
from app.modules.kg.exceptions import KgCannotBeDeletedError, KgNotFoundError
from app.modules.kg.models import KgStatus, KgUnit
from app.modules.kg.service import KgManagementService


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
        role=Role.ADMINISTRATOR,
        name="Administrator",
        login="admin",
    )


def _kg(*, status: KgStatus = KgStatus.REGISTERED) -> KgUnit:
    now = datetime.now(UTC)
    return KgUnit(
        dev_eui="a1b2c3d4e5f60708",
        short_id="kg-000001",
        batch_id=uuid4(),
        status=status,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def dependencies(mocker: MockerFixture) -> tuple[MagicMock, MagicMock]:
    repositories = mocker.patch("app.modules.kg.service.KgRepository")
    repositories.return_value.get_by_dev_eui = AsyncMock()
    repositories.return_value.update_status = AsyncMock()
    repositories.return_value.delete = AsyncMock()
    repositories.return_value.search = AsyncMock()
    audits = mocker.patch("app.modules.kg.service.AuditService")
    audits.from_session.return_value.record = AsyncMock()
    return repositories, audits


def _service() -> KgManagementService:
    return KgManagementService(cast(async_sessionmaker[AsyncSession], _SessionFactory()))


@pytest.mark.unit
async def test_set_status_updates_kg_and_records_status_change(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, audits = dependencies
    kg = _kg()
    repositories.return_value.get_by_dev_eui.return_value = kg

    async def update_status(item: KgUnit, *, status: KgStatus) -> KgUnit:
        item.status = status
        return item

    repositories.return_value.update_status.side_effect = update_status

    updated = await _service().set_status(
        actor=_principal(),
        dev_eui=kg.dev_eui,
        status=KgStatus.TESTING,
    )

    assert updated.status is KgStatus.TESTING
    assert (
        audits.from_session.return_value.record.await_args.kwargs["action"] == "kg.status_changed"
    )
    assert audits.from_session.return_value.record.await_args.kwargs["old_data"] == {
        "status": "REGISTERED"
    }
    assert audits.from_session.return_value.record.await_args.kwargs["new_data"] == {
        "status": "TESTING"
    }


@pytest.mark.unit
async def test_set_status_is_a_noop_when_status_does_not_change(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, audits = dependencies
    kg = _kg(status=KgStatus.PACKED)
    repositories.return_value.get_by_dev_eui.return_value = kg

    updated = await _service().set_status(
        actor=_principal(),
        dev_eui=kg.dev_eui,
        status=KgStatus.PACKED,
    )

    assert updated is kg
    repositories.return_value.update_status.assert_not_awaited()
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_delete_rejects_missing_or_non_registered_kg(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, _ = dependencies
    repositories.return_value.get_by_dev_eui.return_value = None

    with pytest.raises(KgNotFoundError):
        await _service().delete(actor=_principal(), dev_eui="a1b2c3d4e5f60708")

    repositories.return_value.get_by_dev_eui.return_value = _kg(status=KgStatus.TESTING)

    with pytest.raises(KgCannotBeDeletedError):
        await _service().delete(actor=_principal(), dev_eui="a1b2c3d4e5f60708")

    repositories.return_value.delete.assert_not_awaited()


@pytest.mark.unit
async def test_delete_removes_registered_kg_and_records_audit_event(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, audits = dependencies
    kg = _kg()
    repositories.return_value.get_by_dev_eui.return_value = kg

    await _service().delete(actor=_principal(), dev_eui=kg.dev_eui)

    repositories.return_value.delete.assert_awaited_once_with(kg)
    record = audits.from_session.return_value.record.await_args.kwargs
    assert record["action"] == "kg.deleted"
    assert record["old_data"]["status"] == "REGISTERED"


@pytest.mark.unit
async def test_list_forwards_filters_to_repository(
    dependencies: tuple[MagicMock, MagicMock],
) -> None:
    repositories, _ = dependencies
    kg = _kg()
    repositories.return_value.search.return_value = ([kg], 1)
    batch_id = kg.batch_id

    result = await _service().list(
        q="a1b2",
        batch_id=batch_id,
        status=KgStatus.REGISTERED,
        page=2,
        page_size=10,
        sort="dev_eui",
        order="asc",
    )

    assert result == ([kg], 1)
    repositories.return_value.search.assert_awaited_once_with(
        q="a1b2",
        batch_id=batch_id,
        status=KgStatus.REGISTERED,
        page=2,
        page_size=10,
        sort="dev_eui",
        order="asc",
    )
