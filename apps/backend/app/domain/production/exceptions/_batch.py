"""Batch errors."""

from app.lib.exceptions import ApplicationConflictError


class BatchArchivedError(ApplicationConflictError):
    """The batch is archived and cannot be modified (HTTP 409)."""

    code = "batch_archived"
    detail = "Archived batch cannot be modified."


class BatchCompletedError(ApplicationConflictError):
    """The batch is completed and cannot be completed again or deleted (HTTP 409)."""

    code = "batch_completed"
    detail = "Batch is already completed."


class BatchEditWindowExpiredError(ApplicationConflictError):
    """The batch was created too long ago to be edited or deleted (HTTP 409)."""

    code = "batch_edit_window_expired"
    detail = "Batch can no longer be edited or deleted."


class BatchInUseError(ApplicationConflictError):
    """The batch has receipts, shipments, verified or used KG units, so it cannot be deleted (HTTP 409)."""

    code = "batch_in_use"
    detail = (
        "Batch has receipts, shipments, verification history or KG units that are no longer registered; "
        "archive it instead."
    )
