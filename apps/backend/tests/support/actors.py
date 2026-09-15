"""Principal builders for tests that care about roles and permissions."""

from uuid import uuid4

from app.shared.security import CurrentPrincipal, Role


def principal(
    role: Role = Role.ADMINISTRATOR,
    *,
    name: str = "Test Actor",
    login: str = "actor",
) -> CurrentPrincipal:
    """An authenticated actor with the permissions its role really grants."""
    return CurrentPrincipal(
        user_id=uuid4(),
        identity_id=uuid4(),
        session_id=uuid4(),
        role=role,
        name=name,
        login=login,
    )


administrator = principal
