from app.core.exceptions import AppError


class BatchError(AppError):
    """Base exception for batch domain failures."""

    default_message = ""


class BatchNotFoundError(BatchError):
    """The requested batch does not exist."""

    code = "batch_not_found"


class BatchCannotBeDeletedError(BatchError):
    """The batch cannot be deleted because production activity already exists."""

    code = "batch_cannot_be_deleted"


class BatchAlreadyCompletedError(BatchError):
    """The batch is already completed."""

    code = "batch_already_completed"


class BatchArchivedError(BatchError):
    """The archived batch cannot be modified."""

    code = "batch_archived"


class BatchReceiptNotFoundError(BatchError):
    """The requested batch receipt does not exist."""

    code = "batch_receipt_not_found"


class BatchReceiptEditNotAllowedError(BatchError):
    """The batch receipt cannot be edited by the current user."""

    code = "batch_receipt_edit_not_allowed"


class BatchReceiptEditWindowExpiredError(BatchError):
    """The allowed batch receipt edit window has expired."""

    code = "batch_receipt_edit_window_expired"


class BatchReceiptAlreadyVoidedError(BatchError):
    """The batch receipt is already voided."""

    code = "batch_receipt_already_voided"


class BatchShipmentNotFoundError(BatchError):
    """The requested batch shipment does not exist."""

    code = "batch_shipment_not_found"


class BatchShipmentEditNotAllowedError(BatchError):
    """The batch shipment cannot be edited by the current user."""

    code = "batch_shipment_edit_not_allowed"


class BatchShipmentEditWindowExpiredError(BatchError):
    """The allowed batch shipment edit window has expired."""

    code = "batch_shipment_edit_window_expired"


class BatchShipmentAlreadyCompletedError(BatchError):
    """The batch shipment is already completed."""

    code = "batch_shipment_already_completed"


class BatchShipmentAlreadyVoidedError(BatchError):
    """The batch shipment is already voided."""

    code = "batch_shipment_already_voided"


class BatchShipmentEmptyError(BatchError):
    """An empty batch shipment cannot be completed."""

    code = "batch_shipment_empty"


class BatchShipmentItemNotFoundError(BatchError):
    """The requested KG is not present in the shipment."""

    code = "batch_shipment_item_not_found"


class BatchShipmentKgNotFoundError(BatchError):
    """The requested KG does not exist."""

    code = "batch_shipment_kg_not_found"


class BatchShipmentKgWrongBatchError(BatchError):
    """The KG belongs to another batch."""

    code = "batch_shipment_kg_wrong_batch"


class BatchShipmentKgNotPackedError(BatchError):
    """The KG is not ready for shipment."""

    code = "batch_shipment_kg_not_packed"


class BatchShipmentKgAlreadyAssignedError(BatchError):
    """The KG already belongs to another active shipment."""

    code = "batch_shipment_kg_already_assigned"


class BatchEditNotAllowedError(BatchError):
    """The batch cannot be edited by the current user."""

    code = "batch_edit_not_allowed"


class BatchEditWindowExpiredError(BatchError):
    """The allowed batch edit window has expired."""

    code = "batch_edit_window_expired"


class BatchDevEuiPrefixNotFoundError(BatchError):
    """The requested DevEUI prefix does not exist."""

    code = "batch_dev_eui_prefix_not_found"


class BatchDevEuiRangeOverflowError(BatchError):
    """The DevEUI suffix range exceeds six hex characters."""

    code = "batch_dev_eui_range_overflow"
