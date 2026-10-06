"""Realtime events of the production domain."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from app.domain.production.permissions import (
    BatchPermission,
    KgPrefixPermission,
    KgVersionPermission,
    MulticastGroupPermission,
    ProductionOrderPermission,
)
from app.lib.realtime import RealtimeEvent


class BatchChanged(RealtimeEvent):
    """A batch changed: its fields, its receipts or shipments, or the state of its KG units."""

    event_type: ClassVar[str] = "batch.changed"
    permission: ClassVar[str] = BatchPermission.READ

    batch_id: UUID


class KgPrefixChanged(RealtimeEvent):
    """A KG prefix was created, changed or deleted."""

    event_type: ClassVar[str] = "kg_prefix.changed"
    permission: ClassVar[str] = KgPrefixPermission.READ

    prefix_id: UUID


class KgVersionChanged(RealtimeEvent):
    """A KG version was created, changed or deleted."""

    event_type: ClassVar[str] = "kg_version.changed"
    permission: ClassVar[str] = KgVersionPermission.READ

    version_id: UUID


class MulticastGroupChanged(RealtimeEvent):
    """A multicast group was created, changed or deleted."""

    event_type: ClassVar[str] = "multicast_group.changed"
    permission: ClassVar[str] = MulticastGroupPermission.READ

    multicast_group_id: UUID


class ProductionOrderChanged(RealtimeEvent):
    """A production order was created, changed or deleted."""

    event_type: ClassVar[str] = "production_order.changed"
    permission: ClassVar[str] = ProductionOrderPermission.READ

    order_id: UUID


__all__ = (
    "BatchChanged",
    "KgPrefixChanged",
    "KgVersionChanged",
    "MulticastGroupChanged",
    "ProductionOrderChanged",
)
