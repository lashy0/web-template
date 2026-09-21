from __future__ import annotations

import pytest

from app.db.enums import UserRole
from app.domain.accounts.permissions import UserPermission
from app.lib.authorization import PermissionPolicy, has_permission, has_permission_in, permissions_for_role
from app.server.authorization import create_authorization_policy

pytestmark = [pytest.mark.unit, pytest.mark.auth, pytest.mark.security]


def test_initial_policy_grants_exact_users_permissions_only_to_administrators() -> None:
    """The initial role policy preserves explicit administrator-only access."""
    policy = create_authorization_policy()
    expected = frozenset(
        {
            "users.read",
            "users.create",
            "users.update",
            "users.delete",
        }
    )

    assert permissions_for_role(policy, UserRole.ADMINISTRATOR) == expected
    assert permissions_for_role(policy, "administrator") == expected

    for role in (
        UserRole.MANAGER,
        UserRole.ENGINEER,
        UserRole.PACKER,
        UserRole.OPERATOR,
    ):
        assert permissions_for_role(policy, role) == frozenset()


def test_unknown_roles_fail_closed() -> None:
    """Roles absent from the policy receive no permissions."""
    policy = create_authorization_policy()

    assert permissions_for_role(policy, "future-role") == frozenset()
    assert has_permission(policy, "future-role", UserPermission.READ) is False


def test_permissions_require_exact_matching() -> None:
    """Permission matching does not expand wildcards or parent namespaces."""
    policy = create_authorization_policy()

    assert has_permission(policy, UserRole.ADMINISTRATOR, UserPermission.READ)
    assert has_permission(policy, UserRole.ADMINISTRATOR, "users.*") is False
    assert has_permission(policy, UserRole.ADMINISTRATOR, "users") is False


def test_new_domain_permissions_need_explicit_assignment() -> None:
    """A declaration in another namespace does not change production grants."""
    policy = create_authorization_policy()

    assert has_permission(policy, UserRole.ADMINISTRATOR, "quality.inspect") is False


def test_evaluator_supports_permissions_from_other_domains() -> None:
    """The generic evaluator accepts explicitly assigned permissions."""
    policy = PermissionPolicy({"quality-manager": {"quality.inspect"}})

    assert has_permission(policy, "quality-manager", "quality.inspect")
    assert has_permission_in(policy.permissions_for_role("quality-manager"), "quality.inspect")
    assert has_permission(policy, "quality-manager", "quality.update") is False


def test_policy_copies_and_freezes_constructor_inputs() -> None:
    """Changing source mappings cannot mutate an already configured policy."""
    grants = {"manager": {"users.read"}}
    policy = PermissionPolicy(grants)

    grants["manager"].add("users.update")
    grants["other"] = {"users.delete"}

    assert policy.permissions_for_role("manager") == frozenset({"users.read"})
    assert policy.permissions_for_role("other") == frozenset()

    with pytest.raises(TypeError):
        policy.grants["manager"] = frozenset({"users.update"})  # type: ignore[index]

    with pytest.raises(AttributeError):
        policy.permissions_for_role("manager").add("users.update")  # type: ignore[attr-defined]
