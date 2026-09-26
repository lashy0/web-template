"""Permission identifiers owned by the production domain."""

from enum import StrEnum


class ProductionOrderPermission(StrEnum):
    """Capabilities for managing production orders."""

    READ = "production_orders.read"
    CREATE = "production_orders.create"
    UPDATE = "production_orders.update"

    ARCHIVE = "production_orders.archive"

    DELETE = "production_orders.delete"


class KgPrefixPermission(StrEnum):
    """Capabilities for managing the DevEUI prefix catalog."""

    READ = "kg_prefixes.read"
    CREATE = "kg_prefixes.create"
    UPDATE = "kg_prefixes.update"

    ARCHIVE = "kg_prefixes.archive"

    DELETE = "kg_prefixes.delete"


class KgVersionPermission(StrEnum):
    """Capabilities for managing the KG version catalog."""

    READ = "kg_versions.read"
    CREATE = "kg_versions.create"
    UPDATE = "kg_versions.update"

    ARCHIVE = "kg_versions.archive"

    DELETE = "kg_versions.delete"


class KgUnitPermission(StrEnum):
    """Capabilities for viewing KG units of batches; production processes change them."""

    READ = "kg_units.read"


class PackingPermission(StrEnum):
    """Capabilities of the packing workstation."""

    PACK = "packing.pack"


class BatchPermission(StrEnum):
    """Capabilities for managing production batches and their receipts."""

    READ = "batches.read"
    CREATE = "batches.create"
    UPDATE = "batches.update"
    ASSIGN_PRODUCTION_ORDER = "batches.assign_production_order"
    COMPLETE = "batches.complete"
    CREATE_RECEIPT = "batches.receipts.create"
    UPDATE_RECEIPT = "batches.receipts.update"
    VOID_RECEIPT = "batches.receipts.void"

    ARCHIVE = "batches.archive"

    DELETE = "batches.delete"


__all__ = (
    "BatchPermission",
    "KgPrefixPermission",
    "KgUnitPermission",
    "KgVersionPermission",
    "PackingPermission",
    "ProductionOrderPermission",
)
