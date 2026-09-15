"""Central registry of SQLAlchemy models used by Alembic."""

from app.contexts.equipment.pak.model import PakDevice
from app.contexts.identity.users.model import User
from app.contexts.production.batches.model import Batch, BatchLoRaWanConfig
from app.contexts.production.kg.model import KgDevEuiPrefix, KgUnit, KgVersion, LoRaWanCredentials
from app.contexts.production.preparation.model import BatchKeyGenerationJob
from app.contexts.production.production_orders.model import ProductionOrder
from app.contexts.production.receipts.model import BatchReceipt
from app.contexts.production.shipments.model import BatchShipment, BatchShipmentItem
from app.contexts.quality.defects.model import DefectGroup, DefectType
from app.contexts.quality.tests.model import PakTest
from app.contexts.quality.verification.model import VerificationSession, VerificationStep
from app.modules.audit.models import AuditEvent

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
