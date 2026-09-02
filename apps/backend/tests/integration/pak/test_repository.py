from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.defects.repository import DefectGroupRepository
from app.modules.pak.models import PakDeviceKind
from app.modules.pak.repository import PakRepository, PakTestRepository


@pytest.mark.integration
async def test_created_pak_is_retrievable_by_id_and_oauth_client_id(
    db_session: AsyncSession,
) -> None:
    repository = PakRepository(db_session)
    pak_id = uuid4()

    created = await repository.create(
        pak_id=pak_id,
        code="PAK-OTK-01",
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id=f"pak-{pak_id}",
        encrypted_access_key="ciphertext",
    )

    by_id = await repository.get_by_id(created.id)
    by_oauth_client_id = await repository.get_by_oauth_client_id(created.oauth_client_id)

    assert created.id == pak_id
    assert created.last_seen_at is None
    assert by_id is not None
    assert by_id.encrypted_access_key == "ciphertext"
    assert by_oauth_client_id is not None
    assert by_oauth_client_id.id == created.id


@pytest.mark.integration
async def test_pak_details_access_key_and_active_state_can_be_updated(
    db_session: AsyncSession,
) -> None:
    repository = PakRepository(db_session)
    pak_id = uuid4()
    pak = await repository.create(
        pak_id=pak_id,
        code="PAK-OTK-01",
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id=f"pak-{pak_id}",
        encrypted_access_key="first-ciphertext",
    )

    await repository.update_details(pak, code="PAK-OTK-02", kind=PakDeviceKind.ENGINEERING)
    await repository.update_access_key(pak, encrypted_access_key="rotated-ciphertext")
    await repository.update_active(pak, active=False)
    retrieved = await repository.get_by_id(pak.id)

    assert retrieved is not None
    assert retrieved.code == "PAK-OTK-02"
    assert retrieved.kind is PakDeviceKind.ENGINEERING
    assert retrieved.encrypted_access_key == "rotated-ciphertext"
    assert not retrieved.is_active


@pytest.mark.integration
async def test_pak_can_be_archived_and_restored_without_becoming_active(
    db_session: AsyncSession,
) -> None:
    repository = PakRepository(db_session)
    pak_id = uuid4()
    pak = await repository.create(
        pak_id=pak_id,
        code="PAK-OTK-01",
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id=f"pak-{pak_id}",
        encrypted_access_key="ciphertext",
        active=False,
    )

    await repository.update_archived(pak, archived_at=pak.created_at)
    archived, total = await repository.search(
        q=None,
        kind=None,
        active=None,
        archived=True,
        page=1,
        page_size=25,
        sort="code",
        order="asc",
    )
    await repository.update_archived(pak, archived_at=None)
    restored = await repository.get_by_id(pak.id)

    assert total == 1
    assert [item.id for item in archived] == [pak.id]
    assert restored is not None
    assert restored.archived_at is None
    assert not restored.is_active


@pytest.mark.integration
async def test_pak_tests_can_be_created_updated_and_searched(
    db_session: AsyncSession,
) -> None:
    group_repository = DefectGroupRepository(db_session)
    test_repository = PakTestRepository(db_session)
    suffix = uuid4().hex[:8]
    group = await group_repository.create(
        code=f"POWER_{suffix}", name="Power supply", description=None
    )
    observed_at = datetime.now(UTC)
    test = await test_repository.create(
        test_name=f"INSULATION_{suffix}",
        test_label="Insulation resistance",
        defect_group_id=group.id,
        last_seen_at=observed_at,
    )

    updated_at = datetime.now(UTC)
    updated = await test_repository.update_observation(
        test,
        test_label="Insulation check",
        defect_group_id=group.id,
        last_seen_at=updated_at,
    )
    by_id = await test_repository.get_by_id(test.id)
    by_name = await test_repository.get_by_test_name(test.test_name)
    found, total = await test_repository.search(
        q="insulation",
        defect_group_id=group.id,
        page=1,
        page_size=25,
        sort="test_name",
        order="asc",
    )

    assert updated.test_label == "Insulation check"
    assert updated.last_seen_at == updated_at
    assert by_id is not None
    assert by_name is not None
    assert by_name.id == test.id
    assert total == 1
    assert [item.id for item in found] == [test.id]
