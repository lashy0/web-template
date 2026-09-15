"""Production batch-family errors with stable public error codes."""

from app.core.exceptions import AppError, ConflictError, InvalidInputError, NotFoundError


class BatchError(AppError):
    default_message = ""


class BatchNotFoundError(BatchError, NotFoundError):
    code = "batch_not_found"


class BatchConflictError(BatchError, ConflictError):
    code = "batch_conflict"


class BatchShipmentKgStateConflictError(BatchError, ConflictError):
    code = "batch_shipment_kg_state_conflict"


class BatchCannotBeDeletedError(BatchError, ConflictError):
    code = "batch_cannot_be_deleted"


class BatchAlreadyCompletedError(BatchError, ConflictError):
    code = "batch_already_completed"


class BatchArchivedError(BatchError, ConflictError):
    code = "batch_archived"


class BatchPreparationNotReadyError(BatchError, ConflictError):
    code = "batch_preparation_not_ready"


class BatchReceiptNotFoundError(BatchError, NotFoundError):
    code = "batch_receipt_not_found"


class BatchReceiptEditNotAllowedError(BatchError, ConflictError):
    code = "batch_receipt_edit_not_allowed"


class BatchReceiptEditWindowExpiredError(BatchError, ConflictError):
    code = "batch_receipt_edit_window_expired"


class BatchReceiptAlreadyVoidedError(BatchError, ConflictError):
    code = "batch_receipt_already_voided"


class BatchShipmentNotFoundError(BatchError, NotFoundError):
    code = "batch_shipment_not_found"


class BatchShipmentEditNotAllowedError(BatchError, ConflictError):
    code = "batch_shipment_edit_not_allowed"


class BatchShipmentEditWindowExpiredError(BatchError, ConflictError):
    code = "batch_shipment_edit_window_expired"


class BatchShipmentAlreadyCompletedError(BatchError, ConflictError):
    code = "batch_shipment_already_completed"


class BatchShipmentAlreadyVoidedError(BatchError, ConflictError):
    code = "batch_shipment_already_voided"


class BatchShipmentEmptyError(BatchError, ConflictError):
    code = "batch_shipment_empty"


class BatchShipmentItemNotFoundError(BatchError, NotFoundError):
    code = "batch_shipment_item_not_found"


class BatchShipmentKgNotFoundError(BatchError, NotFoundError):
    code = "batch_shipment_kg_not_found"


class BatchShipmentKgWrongBatchError(BatchError, ConflictError):
    code = "batch_shipment_kg_wrong_batch"


class BatchShipmentKgNotPackedError(BatchError, ConflictError):
    code = "batch_shipment_kg_not_packed"


class BatchShipmentKgAlreadyAssignedError(BatchError, ConflictError):
    code = "batch_shipment_kg_already_assigned"


class BatchEditNotAllowedError(BatchError, ConflictError):
    code = "batch_edit_not_allowed"


class BatchEditWindowExpiredError(BatchError, ConflictError):
    code = "batch_edit_window_expired"


class BatchDevEuiPrefixNotFoundError(BatchError, ConflictError):
    code = "batch_dev_eui_prefix_not_found"


class BatchDevEuiRangeOverflowError(BatchError, ConflictError):
    code = "batch_dev_eui_range_overflow"


class BatchKgVersionArchivedError(BatchError, ConflictError):
    code = "batch_kg_version_archived"


class BatchKgVersionNotFoundError(BatchError, NotFoundError):
    code = "batch_kg_version_not_found"


class BatchInvalidFiltersError(BatchError, InvalidInputError):
    code = "batch_invalid_filters"
