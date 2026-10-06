"""Realtime events of the quality domain."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, ClassVar
from uuid import UUID

from app.domain.quality.permissions import DefectPermission, VerificationPermission
from app.lib.realtime import RealtimeEvent, announce_after_commit

if TYPE_CHECKING:
    from app.db import models as m
    from app.lib.realtime import Realtime
    from app.lib.uow import UnitOfWork


class DefectGroupChanged(RealtimeEvent):
    """A defect group was created, changed or deleted."""

    event_type: ClassVar[str] = "defect_group.changed"
    permission: ClassVar[str] = DefectPermission.READ

    group_id: UUID


class DefectTypeChanged(RealtimeEvent):
    """A defect type was created, changed or deleted; the count of its group changes with it."""

    event_type: ClassVar[str] = "defect_type.changed"
    permission: ClassVar[str] = DefectPermission.READ

    type_id: UUID


class PakCheckChanged(RealtimeEvent):
    """A PAK reported a check for the first time or another defect group code for it."""

    event_type: ClassVar[str] = "pak_check.changed"
    permission: ClassVar[str] = VerificationPermission.READ

    check_id: UUID


class VerificationChanged(RealtimeEvent):
    """Verification sessions of a PAK on units of a batch changed: one started, advanced or ended."""

    event_type: ClassVar[str] = "verification.changed"
    permission: ClassVar[str] = VerificationPermission.READ

    pak_id: UUID
    batch_id: UUID


def announce_verification_changes(
    uow: UnitOfWork,
    realtime: Realtime,
    sessions: Iterable[m.VerificationSession],
) -> None:
    """Announce, once the transaction commits, that the sessions changed: once per PAK and batch."""
    for pak_id, batch_id in {(item.pak_id, item.batch_id) for item in sessions}:
        announce_after_commit(uow, realtime, VerificationChanged(pak_id=pak_id, batch_id=batch_id))


__all__ = (
    "DefectGroupChanged",
    "DefectTypeChanged",
    "PakCheckChanged",
    "VerificationChanged",
    "announce_verification_changes",
)
