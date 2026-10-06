"""Realtime events of the accounts domain."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from app.domain.accounts.permissions import UserPermission
from app.lib.realtime import RealtimeEvent


class UserChanged(RealtimeEvent):
    """A user was created, changed or deleted."""

    event_type: ClassVar[str] = "user.changed"
    permission: ClassVar[str] = UserPermission.READ

    user_id: UUID


__all__ = ("UserChanged",)
