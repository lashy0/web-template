from app.shared.security import ForbiddenError

from .model import PakDevice


def ensure_not_archived(pak: PakDevice) -> None:
    if pak.archived_at is not None:
        raise ForbiddenError("Cannot modify an archived PAK")


def is_noop_details(pak: PakDevice, *, code: str | None, kind: object | None) -> bool:
    return (code is None or code == pak.code) and (kind is None or kind == pak.kind)
