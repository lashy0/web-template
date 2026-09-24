"""Production domain errors with stable client-facing codes."""

from app.lib.exceptions import ApplicationConflictError


class ProductionOrderArchivedError(ApplicationConflictError):
    """The production order is archived and cannot be modified (HTTP 409)."""

    code = "production_order_archived"
    detail = "Archived production order cannot be modified."


__all__ = ("ProductionOrderArchivedError",)
