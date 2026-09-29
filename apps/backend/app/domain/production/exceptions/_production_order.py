"""Production order errors."""

from app.lib.exceptions import ApplicationConflictError


class ProductionOrderArchivedError(ApplicationConflictError):
    """The production order is archived and cannot be modified (HTTP 409)."""

    code = "production_order_archived"
    detail = "Archived production order cannot be modified."


class ProductionOrderInUseError(ApplicationConflictError):
    """Batches belong to the production order, so it cannot be deleted (HTTP 409)."""

    code = "production_order_in_use"
    detail = "Production order has batches; archive it instead."
