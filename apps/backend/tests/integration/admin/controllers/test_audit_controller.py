"""Reading the audit log over HTTP."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from app.db import models as m
from app.db.enums import UserRole
from app.lib.uow import unit_of_work

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import AsyncTestClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.integration.conftest import SignIn

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]

NOW = datetime.now(UTC)


async def _add_entries(session: AsyncSession, *entries: m.AuditLog) -> None:
    async with unit_of_work(session):
        session.add_all(entries)


def _entry(target_type: str, target_id: str, *, days_ago: int = 0) -> m.AuditLog:
    return m.AuditLog(
        action=f"{target_type}.updated",
        actor_login="someone",
        target_type=target_type,
        target_id=target_id,
        target_label=f"{target_type} {target_id}",
        created_at=NOW - timedelta(days=days_ago),
    )


async def test_list_filters_by_target_type_newest_first(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    sign_in: SignIn,
) -> None:
    await sign_in()
    await _add_entries(
        session,
        _entry("user", "u1", days_ago=2),
        _entry("pak", "p1", days_ago=1),
        _entry("batch", "b1"),
    )

    response = await client.get("/api/audit", params={"targetTypeIn": ["user", "pak"]})

    assert response.status_code == 200
    assert [(item["targetType"], item["targetId"]) for item in response.json()["items"]] == [
        ("pak", "p1"),
        ("user", "u1"),
    ]


async def test_list_filters_by_target_id(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    sign_in: SignIn,
) -> None:
    await sign_in()
    await _add_entries(session, _entry("batch", "b1"), _entry("batch", "b2"))

    response = await client.get("/api/audit", params={"targetTypeIn": "batch", "targetIdIn": "b2"})

    assert [item["targetLabel"] for item in response.json()["items"]] == ["batch b2"]


async def test_list_filters_by_creation_time(
    client: AsyncTestClient[Litestar],
    session: AsyncSession,
    sign_in: SignIn,
) -> None:
    await sign_in()
    await _add_entries(session, _entry("pak", "old", days_ago=10), _entry("pak", "new"))

    response = await client.get(
        "/api/audit",
        params={"createdAfter": (NOW - timedelta(days=1)).isoformat()},
    )

    assert [item["targetId"] for item in response.json()["items"]] == ["new"]


async def test_list_is_forbidden_to_non_administrators(
    client: AsyncTestClient[Litestar],
    sign_in: SignIn,
) -> None:
    await sign_in(UserRole.MANAGER)

    response = await client.get("/api/audit")

    assert response.status_code == 403
