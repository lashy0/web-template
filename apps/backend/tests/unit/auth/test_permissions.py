import pytest

from app.auth.permissions import (
    ALL_PERMISSIONS,
    MANAGER_PERMISSIONS,
    ENGINEER_PERMISSIONS,
    ROLE_PERMISSIONS,
    permissions_for_role,
    role_has_permission,
)
from app.auth.roles import Role
from app.modules.audit.permissions import AuditPermission
from app.modules.batch.permissions import BatchPermission
from app.modules.kg.permissions import KgPermission
from app.modules.pak.permissions import PakPermission
from app.modules.users.permissions import UserPermission
from app.modules.verification.permissions import VerificationPermission


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
    assert ALL_PERMISSIONS == frozenset(
        (
            *UserPermission,
            *PakPermission,
            *AuditPermission,
            *KgPermission,
            *BatchPermission,
            *VerificationPermission,
        )
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("role", "expected_permissions"),
    [
        pytest.param(Role.MANAGER, MANAGER_PERMISSIONS, id="manager"),
        pytest.param(Role.ENGINEER, ENGINEER_PERMISSIONS, id="engineer"),
        pytest.param(Role.PACKER, frozenset(), id="packer"),
        pytest.param(Role.OPERATOR, frozenset(), id="operator"),
    ],
)
def test_non_administrator_roles_have_expected_permissions(
    role: Role,
    expected_permissions: frozenset,
) -> None:
    permissions = permissions_for_role(role)

    assert permissions == expected_permissions
    assert {
        permission for permission in ALL_PERMISSIONS if role_has_permission(role, permission)
    } == expected_permissions
