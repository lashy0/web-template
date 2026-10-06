"""Multicast group catalog errors."""

from app.lib.exceptions import ApplicationConflictError


class MulticastGroupNameTakenError(ApplicationConflictError):
    """Another multicast group already has the name (HTTP 409)."""

    code = "multicast_group_name_taken"
    detail = "Multicast group name is already registered."


class MulticastGroupArchivedError(ApplicationConflictError):
    """The multicast group is archived and cannot be modified (HTTP 409)."""

    code = "multicast_group_archived"
    detail = "Archived multicast group cannot be modified."


class MulticastGroupInUseError(ApplicationConflictError):
    """Batches use the multicast group (HTTP 409).

    Their KG units are provisioned with it, so only its name may change and it
    cannot be deleted.
    """

    code = "multicast_group_in_use"
    detail = "Multicast group is used by batches; only its name can change, archive it instead of deleting."


class MulticastGroupIdMismatchError(ApplicationConflictError):
    """The multicast group has another group ID than the batch field it was given for (HTTP 409)."""

    code = "multicast_group_id_mismatch"
    detail = "Multicast group has another group ID."
