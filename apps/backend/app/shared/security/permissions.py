"""Permission contracts and immutable registries.

Feature values are deliberately not imported here. The composition root owns
assembling them into the application's registry.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from .roles import Role

type Permission = StrEnum


@dataclass(frozen=True, slots=True)
class PermissionRegistry:
    all_permissions: frozenset[Permission]
    role_permissions: dict[Role, frozenset[Permission]]

    def permissions_for_role(self, role: Role) -> frozenset[Permission]:
        return self.role_permissions[role]

    def role_has_permission(self, role: Role, permission: Permission) -> bool:
        return permission in self.permissions_for_role(role)


EMPTY_PERMISSION_REGISTRY: Final = PermissionRegistry(
    all_permissions=frozenset(), role_permissions={role: frozenset() for role in Role}
)

_registry = EMPTY_PERMISSION_REGISTRY


def install_permission_registry(registry: PermissionRegistry) -> None:
    """Install the process-wide registry assembled by bootstrap."""

    global _registry
    _registry = registry


def permission_registry() -> PermissionRegistry:
    return _registry


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return _registry.permissions_for_role(role)


def role_has_permission(role: Role, permission: Permission) -> bool:
    return _registry.role_has_permission(role, permission)


__all__ = [
    "EMPTY_PERMISSION_REGISTRY",
    "Permission",
    "PermissionRegistry",
    "install_permission_registry",
    "permission_registry",
    "permissions_for_role",
    "role_has_permission",
]
