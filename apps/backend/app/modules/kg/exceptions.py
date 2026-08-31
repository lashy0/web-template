from app.core.exceptions import AppError


class KgError(AppError):
    """Base exception for KG domain failures."""

    default_message = ""


class KgNotFoundError(KgError):
    """The requested KG unit does not exist."""

    code = "kg_not_found"


class KgAlreadyExistsError(KgError):
    """A KG unit with the same DevEUI already exists."""

    code = "kg_already_exists"


class KgCannotBeDeletedError(KgError):
    """The KG unit cannot be deleted in its current state."""

    code = "kg_cannot_be_deleted"


class KgDevEuiPrefixNotFoundError(KgError):
    """The requested DevEUI prefix does not exist."""

    code = "kg_dev_eui_prefix_not_found"


class KgDevEuiPrefixConflictError(KgError):
    """The DevEUI prefix or short code already exists."""

    code = "kg_dev_eui_prefix_conflict"


class KgDevEuiPrefixInUseError(KgError):
    """The DevEUI prefix is already used by a batch."""

    code = "kg_dev_eui_prefix_in_use"
