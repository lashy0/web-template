"""Domain-neutral immutable permission policies and lookup helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

PermissionName = str
RoleName = str


@dataclass(frozen=True, slots=True, init=False)
class PermissionPolicy:
    """An immutable mapping from role names to exact permission names."""

    _grants: Mapping[RoleName, frozenset[PermissionName]]

    def __init__(self, grants: Mapping[Any, Iterable[Any]] | None = None) -> None:
        """Copy and freeze a role grant mapping.

        Both the mapping and every grant collection are copied so later mutation
        of constructor inputs cannot change the configured policy.
        """
        copied_grants = {
            str(role): frozenset(str(permission) for permission in permissions)
            for role, permissions in (grants or {}).items()
        }
        object.__setattr__(self, "_grants", MappingProxyType(copied_grants))

    @property
    def grants(self) -> Mapping[RoleName, frozenset[PermissionName]]:
        """Return the immutable effective grants."""
        return self._grants

    def permissions_for_role(self, role: object) -> frozenset[PermissionName]:
        """Return grants for ``role`` or an empty set when it is unmapped."""
        return self._grants.get(str(role), frozenset())

    def has_permission(self, role: object, permission: object) -> bool:
        """Return whether ``role`` has the exact requested permission."""
        return str(permission) in self.permissions_for_role(role)


def permissions_for_role(policy: PermissionPolicy, role: object) -> frozenset[PermissionName]:
    """Return grants for ``role`` from an explicitly supplied policy."""
    return policy.permissions_for_role(role)


def has_permission(policy: PermissionPolicy, role: object, permission: object) -> bool:
    """Check one exact permission using an explicitly supplied policy."""
    return policy.has_permission(role, permission)


def has_permission_in(grants: Iterable[object], permission: object) -> bool:
    """Check an exact permission against an arbitrary grant collection."""
    return str(permission) in {str(grant) for grant in grants}


__all__ = (
    "PermissionName",
    "PermissionPolicy",
    "RoleName",
    "has_permission",
    "has_permission_in",
    "permissions_for_role",
)
