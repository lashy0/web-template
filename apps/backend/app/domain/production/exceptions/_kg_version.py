"""KG version catalog errors."""

from app.lib.exceptions import ApplicationConflictError


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
