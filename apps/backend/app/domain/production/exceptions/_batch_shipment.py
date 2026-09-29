"""Batch shipment errors."""

from app.lib.exceptions import ApplicationConflictError


class BatchShipmentCompletedError(ApplicationConflictError):
    """The shipment is completed; its details and units no longer change (HTTP 409)."""

    code = "batch_shipment_completed"
    detail = "Completed shipment cannot be changed."


class BatchShipmentVoidedError(ApplicationConflictError):
    """The shipment is voided and cannot be changed (HTTP 409)."""

    code = "batch_shipment_voided"
    detail = "Voided shipment cannot be changed."


class BatchShipmentEmptyError(ApplicationConflictError):
    """The shipment has no KG units, so it cannot be completed (HTTP 409)."""

    code = "batch_shipment_empty"
    detail = "Shipment has no KG units."


class BatchShipmentKgNotPackedError(ApplicationConflictError):
    """A KG unit of the shipment is no longer packed, so the shipment cannot be completed (HTTP 409)."""

    code = "batch_shipment_kg_not_packed"
    detail = "Shipment has KG units that are not packed."


class BatchShipmentVoidWindowExpiredError(ApplicationConflictError):
    """The shipment was completed too long ago to be voided (HTTP 409)."""

    code = "batch_shipment_void_window_expired"
    detail = "Shipment can no longer be voided."
