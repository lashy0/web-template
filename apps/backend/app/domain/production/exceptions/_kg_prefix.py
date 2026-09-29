"""DevEUI prefix catalog errors."""

from app.lib.exceptions import ApplicationConflictError


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
