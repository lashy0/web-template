"""Production domain errors with stable client-facing codes."""

from app.lib.exceptions import ApplicationConflictError


class ProductionOrderArchivedError(ApplicationConflictError):
    """The production order is archived and cannot be modified (HTTP 409)."""

    code = "production_order_archived"
    detail = "Archived production order cannot be modified."


class ProductionOrderInUseError(ApplicationConflictError):
    """Batches belong to the production order, so it cannot be deleted (HTTP 409)."""

    code = "production_order_in_use"
    detail = "Production order has batches; archive it instead."


class KgPrefixTakenError(ApplicationConflictError):
    """Another catalog entry already has the DevEUI prefix (HTTP 409)."""

    code = "kg_prefix_taken"
    detail = "DevEUI prefix is already registered."


class KgPrefixShortCodeTakenError(ApplicationConflictError):
    """Another catalog entry already has the short code (HTTP 409)."""

    code = "kg_prefix_short_code_taken"
    detail = "DevEUI prefix short code is already registered."


class KgPrefixArchivedError(ApplicationConflictError):
    """The DevEUI prefix is archived and cannot be modified (HTTP 409)."""

    code = "kg_prefix_archived"
    detail = "Archived DevEUI prefix cannot be modified."


class KgPrefixInUseError(ApplicationConflictError):
    """DevEUIs were allocated from the prefix, so it cannot be deleted (HTTP 409).

    Deleting it would reset its counter and reissue the allocated DevEUIs.
    """

    code = "kg_prefix_in_use"
    detail = "DevEUIs were allocated from the prefix; archive it instead."


class KgVersionCodeTakenError(ApplicationConflictError):
    """Another KG version already has the code (HTTP 409)."""

    code = "kg_version_code_taken"
    detail = "KG version code is already registered."


class KgVersionArchivedError(ApplicationConflictError):
    """The KG version is archived and cannot be modified (HTTP 409)."""

    code = "kg_version_archived"
    detail = "Archived KG version cannot be modified."


class KgVersionInUseError(ApplicationConflictError):
    """Batches use the KG version, so it cannot be deleted (HTTP 409)."""

    code = "kg_version_in_use"
    detail = "KG version is used by batches; archive it instead."


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
    """Production has already used KG units of the batch, so it cannot be deleted (HTTP 409)."""

    code = "batch_in_use"
    detail = "Batch has KG units that are no longer registered; archive it instead."


__all__ = (
    "BatchArchivedError",
    "BatchCompletedError",
    "BatchEditWindowExpiredError",
    "BatchInUseError",
    "KgPrefixArchivedError",
    "KgPrefixInUseError",
    "KgPrefixShortCodeTakenError",
    "KgPrefixTakenError",
    "KgVersionArchivedError",
    "KgVersionCodeTakenError",
    "KgVersionInUseError",
    "ProductionOrderArchivedError",
    "ProductionOrderInUseError",
)
