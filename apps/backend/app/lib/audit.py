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
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar
from uuid import UUID

type Snapshot = dict[str, Any]


@dataclass(frozen=True, slots=True)
class Actor:
    """Who made a change, with the user's login and name kept as snapshots.

    A PAK or CLI command has a login only; its entries have no user ID or name.
    """

    id: UUID | None = None
    login: str | None = None
    name: str | None = None


class AuditTarget:
    """A model whose records audit entries name as their target.

    The entry's ``target_type`` is ``__audit_type__`` and its ``target_id`` the
    attribute ``__audit_id__``. ``__audit_label__`` names the attribute the
    record is known by, such as a code or a login, and ``__audit_name__`` the
    attribute of a name shown apart from it. The entry keeps both as they were;
    the audit list reads the label again to show one that has changed since.
    """

    __audit_type__: ClassVar[str]
    __audit_id__: ClassVar[str] = "id"
    __audit_label__: ClassVar[str | None] = None
    __audit_name__: ClassVar[str | None] = None


def audit_target_fields(target: AuditTarget) -> dict[str, str | None]:
    """The ``target_*`` fields of an audit entry about ``target``."""
    model = type(target)
    return {
        "target_type": model.__audit_type__,
        "target_id": str(getattr(target, model.__audit_id__)),
        "target_label": _attribute_text(target, model.__audit_label__),
        "target_name": _attribute_text(target, model.__audit_name__),
    }


def audit_target_models() -> dict[str, type[AuditTarget]]:
    """The models audit entries name as targets, by target type."""
    return {model.__audit_type__: model for model in AuditTarget.__subclasses__()}


def _attribute_text(target: AuditTarget, attribute: str | None) -> str | None:
    value = getattr(target, attribute) if attribute else None

    return None if value is None else str(value)


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
    changes = {
        field: {"from": value, "to": after[field]}
        for field, value in before.items()
        if value != after[field]
    }

    return {"changes": changes} if changes else None
