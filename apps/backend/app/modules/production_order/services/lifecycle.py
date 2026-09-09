from app.auth.exceptions import ForbiddenError
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role


def ensure_management_allowed(actor: CurrentPrincipal) -> None:
    if actor.role not in (Role.ADMINISTRATOR, Role.MANAGER):
        raise ForbiddenError
