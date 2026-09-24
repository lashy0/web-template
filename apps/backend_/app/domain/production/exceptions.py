"""Production domain errors with stable client-facing codes."""

from app.lib.exceptions import ApplicationConflictError


class ProductionOrderArchivedError(ApplicationConflictError):
    """The production order is archived and cannot be modified (HTTP 409)."""

    code = "production_order_archived"
    detail = "Archived production order cannot be modified."


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


class KgVersionCodeTakenError(ApplicationConflictError):
    """Another KG version already has the code (HTTP 409)."""

    code = "kg_version_code_taken"
    detail = "KG version code is already registered."


class KgVersionArchivedError(ApplicationConflictError):
    """The KG version is archived and cannot be modified (HTTP 409)."""

    code = "kg_version_archived"
    detail = "Archived KG version cannot be modified."


__all__ = (
    "KgPrefixArchivedError",
    "KgPrefixShortCodeTakenError",
    "KgPrefixTakenError",
    "KgVersionArchivedError",
    "KgVersionCodeTakenError",
    "ProductionOrderArchivedError",
)
