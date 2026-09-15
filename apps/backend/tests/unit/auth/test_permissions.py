import pytest

from app.auth.roles import Role
from app.bootstrap.permissions import (
    ALL_PERMISSIONS,
    ENGINEER_PERMISSIONS,
    MANAGER_PERMISSIONS,
    ROLE_PERMISSIONS,
    compose_permission_registry,
)
from app.contexts.equipment.pak.permissions import PakPermission
from app.contexts.identity.users.permissions import UserPermission
from app.contexts.production.batches.permissions import BatchPermission
from app.contexts.production.kg.permissions import KgPermission
from app.contexts.production.production_orders.permissions import ProductionOrderPermission
from app.contexts.quality.defects.permissions import DefectPermission
from app.contexts.quality.verification.permissions import VerificationPermission
from app.audit.permissions import AuditPermission
from app.shared.security import (
    EMPTY_PERMISSION_REGISTRY,
    install_permission_registry,
    permission_registry,
    permissions_for_role,
    role_has_permission,
)


@pytest.fixture(autouse=True)
def installed_registry() -> None:
    install_permission_registry(compose_permission_registry())


@pytest.mark.unit
def test_every_role_has_a_permission_mapping() -> None:
    assert ROLE_PERMISSIONS.keys() == set(Role)


@pytest.mark.unit
def test_registry_is_empty_until_composition_explicitly_installs_it() -> None:
    install_permission_registry(EMPTY_PERMISSION_REGISTRY)

    assert permission_registry() is EMPTY_PERMISSION_REGISTRY

    registry = compose_permission_registry()
    install_permission_registry(registry)

    assert permission_registry() is registry
    assert registry.permissions_for_role(Role.ADMINISTRATOR) == ALL_PERMISSIONS
    assert registry.permissions_for_role(Role.MANAGER) == MANAGER_PERMISSIONS


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
            *ProductionOrderPermission,
            *DefectPermission,
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
