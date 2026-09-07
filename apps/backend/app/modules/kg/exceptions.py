from app.core.exceptions import AppError, ConflictError, NotFoundError


class KgError(AppError):
    """Base exception for KG domain failures."""

    default_message = ""


class KgConflictError(KgError, ConflictError):
    code = "kg_conflict"


class KgWrongBatchError(KgError, ConflictError):
    code = "kg_wrong_batch"


class KgInvalidStateError(KgError, ConflictError):
    code = "kg_invalid_state"


class KgDevEuiRangeOverflowError(KgError, ConflictError):
    code = "kg_dev_eui_range_overflow"


class KgNotFoundError(KgError, NotFoundError):
    """The requested KG unit does not exist."""

    code = "kg_not_found"


class KgAlreadyExistsError(KgError, ConflictError):
    """A KG unit with the same DevEUI already exists."""

    code = "kg_already_exists"


class KgCannotBeDeletedError(KgError, ConflictError):
    """The KG unit cannot be deleted in its current state."""

    code = "kg_cannot_be_deleted"


class KgDevEuiPrefixNotFoundError(KgError, NotFoundError):
    """The requested DevEUI prefix does not exist."""

    code = "kg_dev_eui_prefix_not_found"


class KgDevEuiPrefixConflictError(KgError, ConflictError):
    """The DevEUI prefix or short code already exists."""

    code = "kg_dev_eui_prefix_conflict"


class KgDevEuiPrefixInUseError(KgError, ConflictError):
    """The DevEUI prefix is already used by a batch."""

    code = "kg_dev_eui_prefix_in_use"


class KgDevEuiPrefixArchivedError(KgError, ConflictError):
    """The DevEUI prefix is archived and cannot allocate new units."""

    code = "kg_dev_eui_prefix_archived"


class KgVersionNotFoundError(KgError, NotFoundError):
    code = "kg_version_not_found"


class KgVersionConflictError(KgError, ConflictError):
    code = "kg_version_conflict"


class KgVersionInUseError(KgError, ConflictError):
    code = "kg_version_in_use"
