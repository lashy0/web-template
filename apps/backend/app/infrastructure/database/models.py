"""Central registry of SQLAlchemy models used by Alembic."""

from app.contexts.production.preparation.model import BatchKeyGenerationJob
from app.contexts.production.production_orders.model import ProductionOrder
from app.contexts.production.receipts.model import BatchReceipt
from app.contexts.production.shipments.model import BatchShipment, BatchShipmentItem
from app.contexts.quality.defects.model import DefectGroup, DefectType
from app.contexts.quality.tests.model import PakTest
from app.modules.audit.models import AuditEvent
from app.modules.batch.models import (
    Batch,
    BatchLoRaWanConfig,
)
from app.modules.kg.models import KgDevEuiPrefix, KgUnit, KgVersion, LoRaWanCredentials
from app.modules.pak.models import PakDevice
from app.modules.users.models import User
from app.modules.verification.models import VerificationSession, VerificationStep

__all__: list[str] = [
    "User",
    "AuditEvent",
    "PakDevice",
    "PakTest",
    "ProductionOrder",
    "Batch",
    "BatchLoRaWanConfig",
    "BatchKeyGenerationJob",
    "BatchReceipt",
    "BatchShipment",
    "BatchShipmentItem",
    "DefectGroup",
    "DefectType",
    "KgUnit",
    "KgDevEuiPrefix",
    "KgVersion",
    "LoRaWanCredentials",
    "VerificationSession",
    "VerificationStep",
]
