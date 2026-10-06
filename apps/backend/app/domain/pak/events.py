"""Realtime events of the PAK domain."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from app.domain.pak.permissions import PakPermission
from app.lib.realtime import RealtimeEvent


class PakChanged(RealtimeEvent):
    """A PAK was created, changed or deleted: its fields, activity, archive state or access key."""

    event_type: ClassVar[str] = "pak.changed"
    permission: ClassVar[str] = PakPermission.READ

    pak_id: UUID


__all__ = ("PakChanged",)
