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


class MulticastGroupPermission(StrEnum):
    """Capabilities for managing the multicast group catalog."""

    READ = "multicast_groups.read"
    READ_KEYS = "multicast_groups.read_keys"
    """See the McKey and session keys of a group."""
    CREATE = "multicast_groups.create"
    UPDATE = "multicast_groups.update"

    ARCHIVE = "multicast_groups.archive"

    DELETE = "multicast_groups.delete"


class KgUnitPermission(StrEnum):
    """Capabilities for viewing KG units of batches; production processes change them."""

    READ = "kg_units.read"
    READ_CREDENTIALS = "kg_units.read_credentials"
    """See the LoRaWAN keys of a unit."""


class PackingPermission(StrEnum):
    """Capabilities of the packing workstation."""

    PACK = "packing.pack"


class BatchPermission(StrEnum):
    """Capabilities for managing production batches, their receipts and shipments."""

    READ = "batches.read"
    CREATE = "batches.create"
    UPDATE = "batches.update"
    ASSIGN_PRODUCTION_ORDER = "batches.assign_production_order"
    COMPLETE = "batches.complete"
    CREATE_RECEIPT = "batches.receipts.create"
    UPDATE_RECEIPT = "batches.receipts.update"
    VOID_RECEIPT = "batches.receipts.void"
    CREATE_SHIPMENT = "batches.shipments.create"
    UPDATE_SHIPMENT = "batches.shipments.update"
    """Change the details and the KG units of an open shipment."""
    COMPLETE_SHIPMENT = "batches.shipments.complete"
    VOID_SHIPMENT = "batches.shipments.void"

    ARCHIVE = "batches.archive"

    DELETE = "batches.delete"


__all__ = (
    "BatchPermission",
    "KgPrefixPermission",
    "KgUnitPermission",
    "KgVersionPermission",
    "MulticastGroupPermission",
    "PackingPermission",
    "ProductionOrderPermission",
)
