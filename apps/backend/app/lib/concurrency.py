"""Edits made from a stale copy of a record are refused.

A form edits the record as it was read. When someone else changed the record
meanwhile, saving the form would silently undo their change, so an update
carries the ``updatedAt`` of the copy it was made from and is refused with
``record_changed`` when the record has changed since. The record must be read
with a row lock first, so a concurrent update cannot slip in between the check
and the write.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from advanced_alchemy.service import schema_dump

from app.lib.exceptions import ApplicationConflictError
from app.lib.schema import CamelizedBaseStruct

if TYPE_CHECKING:
    from advanced_alchemy.mixins import AuditColumns

_VERSION_FIELD = "expected_updated_at"


class RecordChangedError(ApplicationConflictError):
    code = "record_changed"
    detail = "The record has changed since it was read. Read it again and repeat the change."


class VersionedUpdate(CamelizedBaseStruct, kw_only=True):
    """An update of a record, made from the copy the client read."""

    expected_updated_at: datetime
    """The ``updatedAt`` of the copy the change was made from."""


def ensure_unchanged(record: AuditColumns, expected_updated_at: datetime | None) -> None:
    """Refuse the update unless ``record`` is still the copy it was made from.

    ``None`` skips the check, for a change made by the system rather than from a copy.

    Raises:
        RecordChangedError: The record has changed since.
    """
    if expected_updated_at is not None and record.updated_at != expected_updated_at:
        raise RecordChangedError


def update_changes(data: VersionedUpdate) -> dict[str, Any]:
    """The fields ``data`` sets, without its version."""
    return {field: value for field, value in schema_dump(data).items() if field != _VERSION_FIELD}


__all__ = (
    "RecordChangedError",
    "VersionedUpdate",
    "ensure_unchanged",
    "update_changes",
)
