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


__all__ = ("KgPrefixPermission", "KgVersionPermission", "ProductionOrderPermission")
