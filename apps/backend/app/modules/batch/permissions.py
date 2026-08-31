from enum import StrEnum


class BatchPermission(StrEnum):
    CREATE = "batch:create"
    READ = "batch:read"
    UPDATE = "batch:update"
    ARCHIVE = "batch:archive"
    COMPLETE = "batch:complete"
    DELETE = "batch:delete"

    RECEIPT_CREATE = "batch:receipt:create"
    RECEIPT_UPDATE = "batch:receipt:update"
    RECEIPT_VOID = "batch:receipt:void"

    SHIPMENT_CREATE = "batch:shipment:create"
    SHIPMENT_UPDATE = "batch:shipment:update"
    SHIPMENT_COMPLETE = "batch:shipment:complete"
    SHIPMENT_VOID = "batch:shipment:void"
