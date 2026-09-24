"""Permission identifiers owned by the production domain."""

from enum import StrEnum


class ProductionOrderPermission(StrEnum):
    """Capabilities for managing production orders."""

    READ = "production_orders.read"
    CREATE = "production_orders.create"
    UPDATE = "production_orders.update"

    ARCHIVE = "production_orders.archive"

    DELETE = "production_orders.delete"


__all__ = ("ProductionOrderPermission",)
