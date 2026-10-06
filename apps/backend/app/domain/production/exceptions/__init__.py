"""Production domain errors with stable client-facing codes."""

from app.domain.production.exceptions._batch import (
    BatchArchivedError,
    BatchCompletedError,
    BatchEditWindowExpiredError,
    BatchInUseError,
)
from app.domain.production.exceptions._batch_receipt import (
    BatchReceiptEditWindowExpiredError,
    BatchReceiptQuantityExceededError,
    BatchReceiptVoidedError,
)
from app.domain.production.exceptions._batch_shipment import (
    BatchShipmentCompletedError,
    BatchShipmentEmptyError,
    BatchShipmentKgNotPackedError,
    BatchShipmentQuantityChangedError,
    BatchShipmentVoidedError,
    BatchShipmentVoidWindowExpiredError,
)
from app.domain.production.exceptions._kg_prefix import (
    KgPrefixArchivedError,
    KgPrefixInUseError,
    KgPrefixShortCodeTakenError,
    KgPrefixTakenError,
)
from app.domain.production.exceptions._kg_version import (
    KgVersionArchivedError,
    KgVersionCodeTakenError,
    KgVersionInUseError,
)
from app.domain.production.exceptions._multicast_group import (
    MulticastGroupArchivedError,
    MulticastGroupIdMismatchError,
    MulticastGroupInUseError,
    MulticastGroupNameTakenError,
)
from app.domain.production.exceptions._packing import (
    PackingBatchArchivedError,
    PackingKgAlreadyPackedError,
    PackingKgScrappedError,
    PackingOtkInProgressError,
    PackingOtkNotPassedError,
)
from app.domain.production.exceptions._production_order import (
    ProductionOrderArchivedError,
    ProductionOrderInUseError,
)

__all__ = (
    "BatchArchivedError",
    "BatchCompletedError",
    "BatchEditWindowExpiredError",
    "BatchInUseError",
    "BatchReceiptEditWindowExpiredError",
    "BatchReceiptQuantityExceededError",
    "BatchReceiptVoidedError",
    "BatchShipmentCompletedError",
    "BatchShipmentEmptyError",
    "BatchShipmentKgNotPackedError",
    "BatchShipmentQuantityChangedError",
    "BatchShipmentVoidWindowExpiredError",
    "BatchShipmentVoidedError",
    "KgPrefixArchivedError",
    "KgPrefixInUseError",
    "KgPrefixShortCodeTakenError",
    "KgPrefixTakenError",
    "KgVersionArchivedError",
    "KgVersionCodeTakenError",
    "KgVersionInUseError",
    "MulticastGroupArchivedError",
    "MulticastGroupIdMismatchError",
    "MulticastGroupInUseError",
    "MulticastGroupNameTakenError",
    "PackingBatchArchivedError",
    "PackingKgAlreadyPackedError",
    "PackingKgScrappedError",
    "PackingOtkInProgressError",
    "PackingOtkNotPassedError",
    "ProductionOrderArchivedError",
    "ProductionOrderInUseError",
)
