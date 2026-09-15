from app.core.exceptions import AppError, ConflictError, InvalidInputError, NotFoundError


class KgError(AppError):
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
    code = "kg_not_found"


class KgAlreadyExistsError(KgError, ConflictError):
    code = "kg_already_exists"


class KgCannotBeDeletedError(KgError, ConflictError):
    code = "kg_cannot_be_deleted"


class KgLoRaWanCredentialsAlreadyExistError(KgError, ConflictError):
    code = "kg_lorawan_credentials_already_exist"
    default_message = "LoRaWAN credentials already exist for this KG unit"


class KgLoRaWanCredentialsNotFoundError(KgError, NotFoundError):
    code = "kg_lorawan_credentials_not_found"
    default_message = "LoRaWAN credentials do not exist for this KG unit"


class KgLoRaWanConfigurationMissingError(KgError, InvalidInputError):
    code = "kg_lorawan_configuration_missing"
    default_message = "KG batch does not have a LoRaWAN configuration"


class KgDevEuiPrefixNotFoundError(KgError, NotFoundError):
    code = "kg_dev_eui_prefix_not_found"


class KgDevEuiPrefixConflictError(KgError, ConflictError):
    code = "kg_dev_eui_prefix_conflict"


class KgDevEuiPrefixInUseError(KgError, ConflictError):
    code = "kg_dev_eui_prefix_in_use"


class KgDevEuiPrefixArchivedError(KgError, ConflictError):
    code = "kg_dev_eui_prefix_archived"


class KgVersionNotFoundError(KgError, NotFoundError):
    code = "kg_version_not_found"


class KgVersionConflictError(KgError, ConflictError):
    code = "kg_version_conflict"


class KgVersionInUseError(KgError, ConflictError):
    code = "kg_version_in_use"
