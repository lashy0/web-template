"""Batch receipt errors."""

from app.lib.exceptions import ApplicationConflictError


class BatchReceiptQuantityExceededError(ApplicationConflictError):
    """The receipts of a batch would exceed its planned quantity (HTTP 409)."""

    code = "batch_receipt_quantity_exceeded"
    detail = "Receipts cannot exceed the planned quantity of the batch."


class BatchReceiptVoidedError(ApplicationConflictError):
    """The receipt is voided and cannot be changed (HTTP 409)."""

    code = "batch_receipt_voided"
    detail = "Voided receipt cannot be changed."


class BatchReceiptEditWindowExpiredError(ApplicationConflictError):
    """The receipt was created too long ago to be edited or voided (HTTP 409)."""

    code = "batch_receipt_edit_window_expired"
    detail = "Receipt can no longer be edited or voided."
