"""The changes an audit entry records: ``{"changes": {field: {"from": old, "to": new}}}``.

A controller takes a snapshot of the record before the service changes it and
another after, and logs the difference. A field is named as the API names it
and read from a model attribute; a reference to another record is read through
the relationship as a label, such as ``production_order.name``, so the entry
stays readable after that record is renamed or deleted. Secrets are never
snapshotted: their changes have actions of their own, such as
``user.password_changed``.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

type Snapshot = dict[str, Any]


def audit_value(value: object) -> Any:
    """Return ``value`` as JSON can store it."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _read(record: object, path: str) -> object:
    value: object = record
    for attribute in path.split("."):
        if value is None:
            return None
        value = getattr(value, attribute)
    return value


def snapshot(record: object, fields: Mapping[str, str]) -> Snapshot:
    """Read ``fields``, a mapping of field names to attribute paths, from ``record``."""
    return {field: audit_value(_read(record, path)) for field, path in fields.items()}


def same_fields(*names: str) -> dict[str, str]:
    """Fields whose names are the attribute names."""
    return {name: name for name in names}


def change_details(before: Snapshot, after: Snapshot) -> dict[str, Any] | None:
    """Return the ``details`` of the fields that differ, or None when nothing changed."""
    changes = {field: {"from": value, "to": after[field]} for field, value in before.items() if value != after[field]}
    return {"changes": changes} if changes else None
