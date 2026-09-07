from app.auth.exceptions import ForbiddenError

from ..models import PakDevice


def _ensure_not_archived(pak: PakDevice) -> None:
    if pak.archived_at is not None:
        raise ForbiddenError("Cannot modify an archived PAK")
