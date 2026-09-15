from app.core.exceptions import AppError, ConflictError, NotFoundError


class DefectError(AppError):
    default_message = ""


class DefectGroupNotFoundError(DefectError, NotFoundError):
    code = "defect_group_not_found"


class DefectGroupAlreadyExistsError(DefectError, ConflictError):
    code = "defect_group_already_exists"


class DefectGroupArchivedError(DefectError, ConflictError):
    code = "defect_group_archived"


class DefectGroupHasUnarchivedTypesError(DefectError, ConflictError):
    code = "defect_group_has_unarchived_types"


class DefectGroupCannotBeDeletedError(DefectError, ConflictError):
    code = "defect_group_cannot_be_deleted"


class DefectTypeNotFoundError(DefectError, NotFoundError):
    code = "defect_type_not_found"


class DefectTypeAlreadyExistsError(DefectError, ConflictError):
    code = "defect_type_already_exists"


class DefectTypeCannotBeDeletedError(DefectError, ConflictError):
    code = "defect_type_cannot_be_deleted"
