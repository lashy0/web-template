"""Central registry of SQLAlchemy models used by Alembic."""

from app.modules.audit.models import AuditEvent
from app.modules.batch.models import Batch, BatchReceipt, BatchShipment, BatchShipmentItem
from app.modules.defects.models import DefectGroup, DefectType
from app.modules.kg.models import KgDevEuiPrefix, KgUnit
from app.modules.pak.models import PakDevice, PakTest
from app.modules.users.models import User
from app.modules.verification.models import VerificationSession, VerificationStep

__all__: list[str] = [
    "User",
    "AuditEvent",
    "PakDevice",
    "PakTest",
    "Batch",
    "BatchReceipt",
    "BatchShipment",
    "BatchShipmentItem",
    "DefectGroup",
    "DefectType",
    "KgUnit",
    "KgDevEuiPrefix",
    "VerificationSession",
    "VerificationStep",
]
