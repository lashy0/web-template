"""Authenticated application principal; auth adapters only construct it."""

from dataclasses import dataclass
from uuid import UUID

from .permissions import Permission, permissions_for_role
from .roles import Role


@dataclass(frozen=True, slots=True)
class CurrentPrincipal:
    user_id: UUID
    identity_id: UUID
    session_id: UUID
    role: Role
    name: str | None = None
    login: str | None = None

    @property
    def permissions(self) -> frozenset[Permission]:
        return permissions_for_role(self.role)

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions


__all__ = ["CurrentPrincipal"]
