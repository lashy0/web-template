from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.db.enums import UserRole
from app.lib.audit import change_details, same_fields, snapshot

pytestmark = pytest.mark.unit


@dataclass
class _Order:
    name: str


@dataclass
class _Record:
    name: str
    role: UserRole
    order: _Order | None
    owner_id: UUID
    seen_at: datetime


def _record(**changes: object) -> _Record:
    values: dict[str, object] = {
        "name": "Партия 1",
        "role": UserRole.OPERATOR,
        "order": _Order("Заказ 7"),
        "owner_id": UUID(int=1),
        "seen_at": datetime(2026, 9, 29, 10, 0, tzinfo=UTC),
    }
    return _Record(**(values | changes))  # type: ignore[arg-type]


def test_snapshot_stores_json_values_and_follows_references() -> None:
    fields = same_fields("name", "role", "owner_id", "seen_at") | {"order": "order.name"}

    assert snapshot(_record(), fields) == {
        "name": "Партия 1",
        "role": "operator",
        "owner_id": "00000000-0000-0000-0000-000000000001",
        "seen_at": "2026-09-29T10:00:00+00:00",
        "order": "Заказ 7",
    }


def test_snapshot_reads_a_missing_reference_as_none() -> None:
    assert snapshot(_record(order=None), {"order": "order.name"}) == {"order": None}


def test_change_details_lists_only_changed_fields() -> None:
    fields = same_fields("name", "role") | {"order": "order.name"}
    before = snapshot(_record(), fields)
    after = snapshot(_record(role=UserRole.ADMINISTRATOR, order=None), fields)

    assert change_details(before, after) == {
        "changes": {
            "role": {"from": "operator", "to": "administrator"},
            "order": {"from": "Заказ 7", "to": None},
        }
    }


def test_change_details_is_none_without_changes() -> None:
    fields = same_fields("name")

    assert change_details(snapshot(_record(), fields), snapshot(_record(), fields)) is None
