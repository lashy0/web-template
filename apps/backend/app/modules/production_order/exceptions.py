from app.core.exceptions import AppError, ConflictError, NotFoundError


class ProductionOrderError(AppError):
    default_message = ""


class ProductionOrderNotFoundError(ProductionOrderError, NotFoundError):
    code = "production_order_not_found"


class ProductionOrderArchivedError(ProductionOrderError, ConflictError):
    code = "production_order_archived"


class ProductionOrderCannotBeDeletedError(ProductionOrderError, ConflictError):
    code = "production_order_cannot_be_deleted"


class ProductionOrderConflictError(ProductionOrderError, ConflictError):
    code = "production_order_conflict"
