from uuid import UUID

from app.shared.security import CurrentPrincipal, ForbiddenError, Role

from .model import User

BOOTSTRAP_ADMIN_USER_ID_NAMESPACE = "web-app/bootstrap-administrator/v1"


def ensure_not_system_administrator(user_id: UUID) -> None:
    from uuid import NAMESPACE_URL, uuid5

    if user_id == uuid5(NAMESPACE_URL, BOOTSTRAP_ADMIN_USER_ID_NAMESPACE):
        raise ForbiddenError("Cannot modify the system administrator")


def ensure_not_archived(user: User) -> None:
    if user.archived_at is not None:
        raise ForbiddenError("Cannot modify an archived user")


def ensure_self_administrator_role(actor: CurrentPrincipal, user: User, role: Role | None) -> None:
    if role is not None and user.id == actor.user_id and role != Role.ADMINISTRATOR:
        raise ForbiddenError("Cannot remove your own administrator role")


def ensure_not_self(actor: CurrentPrincipal, user: User, *, action: str) -> None:
    if user.id == actor.user_id:
        raise ForbiddenError(f"Cannot {action} yourself")
