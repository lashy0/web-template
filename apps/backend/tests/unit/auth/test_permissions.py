import pytest

from app.auth.permissions import (
    ALL_PERMISSIONS,
    ROLE_PERMISSIONS,
    permissions_for_role,
    role_has_permission,
)
from app.auth.roles import Role
from app.modules.audit.permissions import AuditPermission
from app.modules.pak.permissions import PakPermission
from app.modules.users.permissions import UserPermission


@pytest.mark.unit
def test_every_role_has_a_permission_mapping() -> None:
    assert ROLE_PERMISSIONS.keys() == set(Role)


@pytest.mark.unit
def test_administrator_has_every_permission() -> None:
    permissions = permissions_for_role(Role.ADMINISTRATOR)

    assert permissions == ALL_PERMISSIONS
    assert all(
        role_has_permission(Role.ADMINISTRATOR, permission) for permission in ALL_PERMISSIONS
    )


@pytest.mark.unit
def test_all_permissions_are_declared_by_modules() -> None:
    assert ALL_PERMISSIONS == frozenset((*UserPermission, *PakPermission, *AuditPermission))


@pytest.mark.unit
@pytest.mark.parametrize(
    "role",
    [
        pytest.param(Role.MANAGER, id="manager"),
        pytest.param(Role.ENGINEER, id="engineer"),
        pytest.param(Role.PACKER, id="packer"),
        pytest.param(Role.OPERATOR, id="operator"),
    ],
)
def test_non_administrator_roles_have_no_permissions_yet(role: Role) -> None:
    permissions = permissions_for_role(role)

    assert permissions == frozenset()
    assert not any(role_has_permission(role, permission) for permission in ALL_PERMISSIONS)
