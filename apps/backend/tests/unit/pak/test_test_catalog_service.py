from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.defects.models import DefectGroup
from app.modules.pak.exceptions import PakTestConfigurationError, PakTestNotFoundError
from app.modules.pak.models import PakDevice, PakDeviceKind, PakTest
from app.modules.pak.service import PakTestCatalogService


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


def _pak() -> PakDevice:
    return PakDevice(
        id=uuid4(),
        code="PAK-OTK-01",
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id="pak-test",
        encrypted_access_key="ciphertext",
        is_active=True,
    )


def _group(*, archived_at: datetime | None = None) -> DefectGroup:
    now = datetime.now(UTC)
    return DefectGroup(
        id=uuid4(),
        code="POWER",
        name="Power supply",
        description=None,
        archived_at=archived_at,
        created_at=now,
        updated_at=now,
    )


def _test(group: DefectGroup) -> PakTest:
    now = datetime.now(UTC)
    return PakTest(
        id=uuid4(),
        test_name="INSULATION_RESISTANCE",
        test_label="Insulation resistance",
        defect_group_id=group.id,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def dependencies(mocker: MockerFixture) -> tuple[MagicMock, MagicMock, MagicMock]:
    groups = mocker.patch("app.modules.pak.service.DefectGroupRepository")
    groups.return_value.get_by_code = AsyncMock()
    groups.return_value.get_by_id = AsyncMock()
    tests = mocker.patch("app.modules.pak.service.PakTestRepository")
    tests.return_value.get_by_id = AsyncMock()
    tests.return_value.get_by_test_name = AsyncMock()
    tests.return_value.create = AsyncMock()
    tests.return_value.update_observation = AsyncMock()
    audits = mocker.patch("app.modules.pak.service.AuditService")
    audits.from_session.return_value.record = AsyncMock()
    return groups, tests, audits


def _service() -> PakTestCatalogService:
    return PakTestCatalogService(cast(async_sessionmaker[AsyncSession], _SessionFactory()))


@pytest.mark.unit
async def test_observe_creates_new_pak_test_and_audits_catalog_entry(
    dependencies: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    groups, tests, audits = dependencies
    pak = _pak()
    group = _group()
    test = _test(group)
    observed_at = datetime(2026, 9, 2, 8, 30, tzinfo=UTC)
    groups.return_value.get_by_code.return_value = group
    tests.return_value.get_by_test_name.return_value = None
    tests.return_value.create.return_value = test

    observed = await _service().observe(
        pak=pak,
        test_name=test.test_name,
        test_label=test.test_label,
        defect_group_code=group.code,
        seen_at=observed_at,
    )

    assert observed is test
    tests.return_value.create.assert_awaited_once_with(
        test_name=test.test_name,
        test_label=test.test_label,
        defect_group_id=group.id,
        last_seen_at=observed_at,
    )
    record = audits.from_session.return_value.record.await_args.kwargs
    assert record["action"] == "pak_test.created"
    assert record["new_data"] == {
        "test_name": test.test_name,
        "test_label": test.test_label,
        "defect_group_id": str(group.id),
        "defect_group_code": group.code,
    }


@pytest.mark.unit
async def test_observe_updates_changed_catalog_metadata_and_audits_delta(
    dependencies: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    groups, tests, audits = dependencies
    pak = _pak()
    previous_group = _group()
    group = _group()
    group.code = "MECHANICAL"
    test = _test(previous_group)
    observed_at = datetime(2026, 9, 2, 8, 30, tzinfo=UTC)
    groups.return_value.get_by_code.return_value = group
    groups.return_value.get_by_id.return_value = previous_group
    tests.return_value.get_by_test_name.return_value = test
    tests.return_value.update_observation.return_value = test

    observed = await _service().observe(
        pak=pak,
        test_name=test.test_name,
        test_label="Insulation check",
        defect_group_code=group.code,
        seen_at=observed_at,
    )

    assert observed is test
    tests.return_value.update_observation.assert_awaited_once_with(
        test,
        test_label="Insulation check",
        defect_group_id=group.id,
        last_seen_at=observed_at,
    )
    record = audits.from_session.return_value.record.await_args.kwargs
    assert record["action"] == "pak_test.updated"
    assert record["old_data"] == {
        "test_label": "Insulation resistance",
        "defect_group_id": str(previous_group.id),
        "defect_group_code": previous_group.code,
    }
    assert record["new_data"] == {
        "test_label": "Insulation check",
        "defect_group_id": str(group.id),
        "defect_group_code": group.code,
    }


@pytest.mark.unit
@pytest.mark.parametrize("archived", [False, True])
async def test_observe_rejects_unknown_or_archived_defect_group(
    dependencies: tuple[MagicMock, MagicMock, MagicMock], archived: bool
) -> None:
    groups, tests, audits = dependencies
    pak = _pak()
    groups.return_value.get_by_code.return_value = (
        _group(archived_at=datetime.now(UTC)) if archived else None
    )

    with pytest.raises(PakTestConfigurationError):
        await _service().observe(
            pak=pak,
            test_name="INSULATION_RESISTANCE",
            test_label="Insulation resistance",
            defect_group_code="POWER",
        )

    tests.return_value.get_by_test_name.assert_not_awaited()
    audits.from_session.return_value.record.assert_not_awaited()


@pytest.mark.unit
async def test_require_raises_when_pak_test_does_not_exist(
    dependencies: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    _, tests, _ = dependencies
    test_id = uuid4()
    tests.return_value.get_by_id.return_value = None

    with pytest.raises(PakTestNotFoundError):
        await _service().require(test_id)

    tests.return_value.get_by_id.assert_awaited_once_with(test_id)
