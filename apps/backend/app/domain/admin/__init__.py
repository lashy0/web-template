"""Admin domain for system administration and audit logging."""

from app.domain.admin import controllers, deps, schemas, services
from app.domain.admin.permissions import AuditPermission

__all__ = (
    "AuditPermission",
    "controllers",
    "deps",
    "schemas",
    "services",
)
