"""Production API schemas."""

from app.domain.production.schemas._batch import (
    Batch,
    BatchCreate,
    BatchCreator,
    BatchKgPrefix,
    BatchKgVersion,
    BatchProductionOrder,
    BatchProductionOrderAssignment,
    BatchUpdate,
    DevEuiRange,
)
from app.domain.production.schemas._kg_prefix import (
    KgPrefix,
    KgPrefixCreate,
    KgPrefixUpdate,
)
from app.domain.production.schemas._kg_unit import KgUnit, KgUnitBatch
from app.domain.production.schemas._kg_version import (
    KgVersion,
    KgVersionCreate,
    KgVersionUpdate,
)
from app.domain.production.schemas._production_order import (
    ProductionOrder,
    ProductionOrderCreate,
    ProductionOrderUpdate,
)

__all__ = (
    "Batch",
    "BatchCreate",
    "BatchCreator",
    "BatchKgPrefix",
    "BatchKgVersion",
    "BatchProductionOrder",
    "BatchProductionOrderAssignment",
    "BatchUpdate",
    "DevEuiRange",
    "KgPrefix",
    "KgPrefixCreate",
    "KgPrefixUpdate",
    "KgUnit",
    "KgUnitBatch",
    "KgVersion",
    "KgVersionCreate",
    "KgVersionUpdate",
    "ProductionOrder",
    "ProductionOrderCreate",
    "ProductionOrderUpdate",
)
