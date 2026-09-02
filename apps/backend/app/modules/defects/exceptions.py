from app.core.exceptions import AppError


class DefectError(AppError):
    """Base exception for defect domain failures."""

    default_message = ""


class DefectGroupNotFoundError(DefectError):
    """The requested defect group does not exist."""

    code = "defect_group_not_found"


class DefectGroupAlreadyExistsError(DefectError):
    """A defect group with the same code already exists."""

    code = "defect_group_already_exists"


class DefectGroupArchivedError(DefectError):
    """The archived defect group cannot be used for new defect types."""

    code = "defect_group_archived"


class DefectGroupHasUnarchivedTypesError(DefectError):
    """The defect group cannot be archived while it contains unarchived defect types."""

    code = "defect_group_has_unarchived_types"


class DefectGroupCannotBeDeletedError(DefectError):
    """The defect group cannot be deleted because it is already in use."""

    code = "defect_group_cannot_be_deleted"


class DefectTypeNotFoundError(DefectError):
    """The requested defect type does not exist."""

    code = "defect_type_not_found"


class DefectTypeAlreadyExistsError(DefectError):
    """A defect type with the same code already exists."""

    code = "defect_type_already_exists"


class DefectTypeCannotBeDeletedError(DefectError):
    """The defect type cannot be deleted because it is already in use."""

    code = "defect_type_cannot_be_deleted"
