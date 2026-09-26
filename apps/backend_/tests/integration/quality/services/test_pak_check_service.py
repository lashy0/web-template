"""PAK check catalog service integration tests against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import models as m
    from app.domain.quality.services import CheckObservation, PakCheckService
    from tests.integration.quality.conftest import CreateGroup, CreatePak

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.services,
]


async def _observe(
    session: AsyncSession,
    pak_check_service: PakCheckService,
    pak: m.PakDevice,
    *,
    name: str = "rf_power",
    label: str = "RF power",
    defect_group_code: str = "RF",
    seen_at: datetime | None = None,
) -> CheckObservation:
    async with unit_of_work(session):
        return await pak_check_service.observe(
            pak=pak,
            name=name,
            label=label,
            defect_group_code=defect_group_code,
            seen_at=seen_at or datetime.now(UTC),
        )


async def test_observe_new_check_creates_it_in_the_group(
    session: AsyncSession,
    pak_check_service: PakCheckService,
    create_pak: CreatePak,
    create_group: CreateGroup,
) -> None:
    group = await create_group("RF")
    pak = await create_pak()

    observation = await _observe(session, pak_check_service, pak)

    assert (observation.created, observation.check.defect_group_id) == (True, group.id)


async def test_observe_known_check_reports_changed_fields(
    session: AsyncSession,
    pak_check_service: PakCheckService,
    create_pak: CreatePak,
) -> None:
    pak = await create_pak()
    await _observe(session, pak_check_service, pak, defect_group_code="RF")

    observation = await _observe(session, pak_check_service, pak, defect_group_code="RADIO")

    assert observation.changes == {"defect_group_code": {"old": "RF", "new": "RADIO"}}


async def test_observe_same_name_with_another_label_is_another_check(
    session: AsyncSession,
    pak_check_service: PakCheckService,
    create_pak: CreatePak,
) -> None:
    pak = await create_pak()
    first = await _observe(
        session, pak_check_service, pak, name="TestDimming", label="Проверка диммирования 0%"
    )

    second = await _observe(
        session, pak_check_service, pak, name="TestDimming", label="Проверка диммирования 20%"
    )

    assert second.created
    assert (first.check.id != second.check.id, first.check.label) == (True, "Проверка диммирования 0%")


async def test_observe_unchanged_check_reports_no_changes(
    session: AsyncSession,
    pak_check_service: PakCheckService,
    create_pak: CreatePak,
) -> None:
    pak = await create_pak()
    await _observe(session, pak_check_service, pak)

    observation = await _observe(session, pak_check_service, pak)

    assert (observation.created, observation.changes) == (False, {})


async def test_observe_unknown_defect_group_keeps_the_check_misconfigured(
    session: AsyncSession,
    pak_check_service: PakCheckService,
    create_pak: CreatePak,
) -> None:
    pak = await create_pak()

    observation = await _observe(session, pak_check_service, pak, defect_group_code="UNKNOWN")

    assert (observation.check.defect_group_code, observation.check.misconfigured) == ("UNKNOWN", True)


async def test_observe_archived_defect_group_leaves_the_check_without_a_group(
    session: AsyncSession,
    pak_check_service: PakCheckService,
    create_pak: CreatePak,
    create_group: CreateGroup,
) -> None:
    await create_group("RF", archived=True)
    pak = await create_pak()

    observation = await _observe(session, pak_check_service, pak)

    assert observation.check.defect_group_id is None


async def test_observe_known_code_later_links_a_misconfigured_check(
    session: AsyncSession,
    pak_check_service: PakCheckService,
    create_pak: CreatePak,
    create_group: CreateGroup,
) -> None:
    pak = await create_pak()
    await _observe(session, pak_check_service, pak)
    group = await create_group("RF")

    observation = await _observe(session, pak_check_service, pak)

    assert (observation.check.defect_group_id, observation.check.defect_group) == (group.id, group)


async def test_observe_older_report_keeps_the_latest_seen_time(
    session: AsyncSession,
    pak_check_service: PakCheckService,
    create_pak: CreatePak,
) -> None:
    pak = await create_pak()
    latest = datetime.now(UTC)
    await _observe(session, pak_check_service, pak, seen_at=latest)

    observation = await _observe(session, pak_check_service, pak, seen_at=latest - timedelta(minutes=5))

    assert observation.check.last_seen_at == latest
