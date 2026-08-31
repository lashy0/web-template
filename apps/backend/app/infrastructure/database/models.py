"""Central registry of SQLAlchemy models used by Alembic."""

from app.modules.audit.models import AuditEvent
from app.modules.batch.models import Batch, BatchReceipt, BatchShipment, BatchShipmentItem
from app.modules.kg.models import KgDevEuiPrefix, KgUnit
from app.modules.pak.models import PakDevice
from app.modules.users.models import User

__all__: list[str] = [
    "User",
    "AuditEvent",
    "PakDevice",
    "Batch",
    "BatchReceipt",
    "BatchShipment",
    "BatchShipmentItem",
    "KgUnit",
    "KgDevEuiPrefix",
]
