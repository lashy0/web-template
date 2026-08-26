"""Central registry of SQLAlchemy models used by Alembic."""

from app.modules.audit.models import AuditEvent
from app.modules.users.models import User

__all__: list[str] = [
    "User",
    "AuditEvent",
]
