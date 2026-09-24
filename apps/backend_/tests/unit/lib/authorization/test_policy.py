import pytest

from app.lib.authorization import PermissionPolicy

pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.security,
]


def test_policy_grants_assigned_permission() -> None:
    policy = PermissionPolicy({"manager": {"users.read"}})

    assert policy.has_permission("manager", "users.read") is True
    assert policy.has_permission("manager", "users.update") is False


def test_policy_unknown_role_has_no_permissions() -> None:
    policy = PermissionPolicy({"manager": {"users.read"}})

    assert policy.permissions_for_role("unknown") == frozenset()


def test_policy_requires_exact_permission() -> None:
    policy = PermissionPolicy({"manager": {"users.read"}})

    assert policy.has_permission("manager", "users.*") is False
