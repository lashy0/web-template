from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from app.auth.permissions import Permission, permissions_for_role
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role


@pytest.mark.unit
@pytest.mark.parametrize(
    ("role", "permission", "expected"),
    [
        pytest.param(
            Role.ADMINISTRATOR,
            Permission.USER_READ,
            True,
            id="allowed",
        ),
        pytest.param(
            Role.OPERATOR,
            Permission.USER_READ,
            False,
            id="forbidden",
        ),
    ],
)
def test_principal_resolves_permissions_from_role(
    role: Role,
    permission: Permission,
    expected: bool,
) -> None:
    principal = CurrentPrincipal(
        user_id=uuid4(),
        identity_id=uuid4(),
        session_id=uuid4(),
        role=role,
    )

    assert principal.permissions == permissions_for_role(role)
    assert principal.has_permission(permission) is expected


@pytest.mark.unit
def test_principal_cannot_be_modified_during_request() -> None:
    principal = CurrentPrincipal(
        user_id=uuid4(),
        identity_id=uuid4(),
        session_id=uuid4(),
        role=Role.ADMINISTRATOR,
    )

    with pytest.raises(FrozenInstanceError):
        principal.role = Role.OPERATOR  # type: ignore[misc]
