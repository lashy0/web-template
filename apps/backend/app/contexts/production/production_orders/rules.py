from app.shared.security import CurrentPrincipal, ForbiddenError, Role


def ensure_management_allowed(actor: CurrentPrincipal) -> None:
    if actor.role not in (Role.ADMINISTRATOR, Role.MANAGER):
        raise ForbiddenError
