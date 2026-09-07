from app.core.exceptions import AppError, ConflictError, NotFoundError


class BatchError(AppError):
    """Base exception for batch domain failures."""

    default_message = ""


class BatchNotFoundError(BatchError, NotFoundError):
    """The requested batch does not exist."""

    code = "batch_not_found"


class BatchConflictError(BatchError, ConflictError):
    """A concurrent change or storage invariant prevents the operation."""

    code = "batch_conflict"


class BatchShipmentKgStateConflictError(BatchError, ConflictError):
    """Shipment cancellation cannot restore a KG whose state has changed."""

    code = "batch_shipment_kg_state_conflict"


class BatchCannotBeDeletedError(BatchError, ConflictError):
    """The batch cannot be deleted because production activity already exists."""

    code = "batch_cannot_be_deleted"


class BatchAlreadyCompletedError(BatchError, ConflictError):
    """The batch is already completed."""

    code = "batch_already_completed"


class BatchArchivedError(BatchError, ConflictError):
    """The archived batch cannot be modified."""

    code = "batch_archived"


class BatchReceiptNotFoundError(BatchError, NotFoundError):
    """The requested batch receipt does not exist."""

    code = "batch_receipt_not_found"


class BatchReceiptEditNotAllowedError(BatchError, ConflictError):
    """The batch receipt cannot be edited by the current user."""

    code = "batch_receipt_edit_not_allowed"


class BatchReceiptEditWindowExpiredError(BatchError, ConflictError):
    """The allowed batch receipt edit window has expired."""

    code = "batch_receipt_edit_window_expired"


class BatchReceiptAlreadyVoidedError(BatchError, ConflictError):
    """The batch receipt is already voided."""

    code = "batch_receipt_already_voided"


class BatchShipmentNotFoundError(BatchError, NotFoundError):
    """The requested batch shipment does not exist."""

    code = "batch_shipment_not_found"


class BatchShipmentEditNotAllowedError(BatchError, ConflictError):
    """The batch shipment cannot be edited by the current user."""

    code = "batch_shipment_edit_not_allowed"


class BatchShipmentEditWindowExpiredError(BatchError, ConflictError):
    """The allowed batch shipment edit window has expired."""

    code = "batch_shipment_edit_window_expired"


class BatchShipmentAlreadyCompletedError(BatchError, ConflictError):
    """The batch shipment is already completed."""

    code = "batch_shipment_already_completed"


class BatchShipmentAlreadyVoidedError(BatchError, ConflictError):
    """The batch shipment is already voided."""

    code = "batch_shipment_already_voided"


class BatchShipmentEmptyError(BatchError, ConflictError):
    """An empty batch shipment cannot be completed."""

    code = "batch_shipment_empty"


class BatchShipmentItemNotFoundError(BatchError, NotFoundError):
    """The requested KG is not present in the shipment."""

    code = "batch_shipment_item_not_found"


class BatchShipmentKgNotFoundError(BatchError, NotFoundError):
    """The requested KG does not exist."""

    code = "batch_shipment_kg_not_found"


class BatchShipmentKgWrongBatchError(BatchError, ConflictError):
    """The KG belongs to another batch."""

    code = "batch_shipment_kg_wrong_batch"


class BatchShipmentKgNotPackedError(BatchError, ConflictError):
    """The KG is not ready for shipment."""

    code = "batch_shipment_kg_not_packed"


class BatchShipmentKgAlreadyAssignedError(BatchError, ConflictError):
    """The KG already belongs to another active shipment."""

    code = "batch_shipment_kg_already_assigned"


class BatchEditNotAllowedError(BatchError, ConflictError):
    """The batch cannot be edited by the current user."""

    code = "batch_edit_not_allowed"


class BatchEditWindowExpiredError(BatchError, ConflictError):
    """The allowed batch edit window has expired."""

    code = "batch_edit_window_expired"


class BatchDevEuiPrefixNotFoundError(BatchError, ConflictError):
    """The requested DevEUI prefix does not exist."""

    code = "batch_dev_eui_prefix_not_found"


class BatchDevEuiRangeOverflowError(BatchError, ConflictError):
    """The DevEUI suffix range exceeds six hex characters."""

    code = "batch_dev_eui_range_overflow"
