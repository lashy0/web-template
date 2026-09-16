"""Central registry of SQLAlchemy models used by Alembic."""

from app.audit.model import AuditEvent
from app.domains.equipment.pak.model import PakDevice
from app.domains.identity.users.model import User
from app.domains.production.batches.model import Batch, BatchLoRaWanConfig
from app.domains.production.kg.model import KgDevEuiPrefix, KgUnit, KgVersion, LoRaWanCredentials
from app.domains.production.orders.model import ProductionOrder
from app.domains.production.preparation.model import BatchKeyGenerationJob
from app.domains.production.receipts.model import BatchReceipt
from app.domains.production.shipments.model import BatchShipment, BatchShipmentItem
from app.domains.quality.checks.model import Check
from app.domains.quality.defects.model import DefectGroup, DefectType
from app.domains.quality.verification.model import VerificationSession, VerificationStep

__all__: list[str] = [
    "User",
    "AuditEvent",
    "PakDevice",
    "Check",
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
