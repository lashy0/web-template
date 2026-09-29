"""Packing errors."""

from app.lib.exceptions import ApplicationConflictError


class PackingKgAlreadyPackedError(ApplicationConflictError):
    """The KG unit is already packed; packing is final (HTTP 409)."""

    code = "packing_kg_already_packed"
    detail = "KG unit is already packed."


class PackingKgScrappedError(ApplicationConflictError):
    """The KG unit is scrapped and cannot be packed (HTTP 409)."""

    code = "packing_kg_scrapped"
    detail = "Scrapped KG unit cannot be packed."


class PackingBatchArchivedError(ApplicationConflictError):
    """The batch of the KG unit is archived, so the unit cannot be packed (HTTP 409)."""

    code = "packing_batch_archived"
    detail = "KG unit of an archived batch cannot be packed."


class PackingOtkInProgressError(ApplicationConflictError):
    """An OTK-line PAK is verifying the KG unit right now (HTTP 409)."""

    code = "packing_otk_in_progress"
    detail = "KG unit is being verified on an OTK-line PAK."


class PackingOtkNotPassedError(ApplicationConflictError):
    """The KG unit has not passed OTK, or its last OTK failed (HTTP 409)."""

    code = "packing_otk_not_passed"
    detail = "KG unit has not passed OTK."
