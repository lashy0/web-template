from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

import msgspec

from app.db.enums import BatchShipmentStatus
from app.domain.production.schemas._batch import UserSummary
from app.domain.production.schemas._batch_receipt import VOID_REASON_MAX_LENGTH, VoidReason
from app.domain.production.schemas._common import Description, validate_description, validate_title
from app.lib.schema import CamelizedBaseStruct

RECIPIENT_MAX_LENGTH = 256
WAYBILL_NUMBER_MAX_LENGTH = 64
Recipient = Annotated[str, msgspec.Meta(min_length=1, max_length=RECIPIENT_MAX_LENGTH)]
WaybillNumber = Annotated[str, msgspec.Meta(min_length=1, max_length=WAYBILL_NUMBER_MAX_LENGTH)]
UNIT_CODES_MAX = 1000
"""How many units one request may add by code; a larger list goes in several requests."""

UnitCodes = Annotated[
    list[str],
    msgspec.Meta(
        min_length=1,
        max_length=UNIT_CODES_MAX,
        description="DevEUIs or short IDs as scanned, in any case.",
    ),
]


class BatchShipment(CamelizedBaseStruct):
    id: UUID
    batch_id: UUID
    number: int
    status: BatchShipmentStatus
    recipient: str | None
    waybill_number: str | None
    comment: str | None
    quantity: int
    created_by: UserSummary | None
    completed_at: datetime | None
    voided_at: datetime | None
    void_reason: str | None
    created_at: datetime
    updated_at: datetime


class BatchShipmentCreate(CamelizedBaseStruct):
    """Open a shipment of the batch; its KG units are added afterwards."""

    recipient: Recipient | None = None
    waybill_number: WaybillNumber | None = None
    comment: Description | None = None

    def __post_init__(self) -> None:
        if self.recipient is not None:
            self.recipient = validate_title(self.recipient, max_length=RECIPIENT_MAX_LENGTH)

        if self.waybill_number is not None:
            self.waybill_number = validate_title(self.waybill_number, max_length=WAYBILL_NUMBER_MAX_LENGTH)

        if self.comment is not None:
            self.comment = validate_description(self.comment)


class BatchShipmentUpdate(CamelizedBaseStruct, omit_defaults=True):
    """Change an open shipment; ``null`` clears a field."""

    recipient: Recipient | msgspec.UnsetType | None = msgspec.UNSET
    waybill_number: WaybillNumber | msgspec.UnsetType | None = msgspec.UNSET
    comment: Description | msgspec.UnsetType | None = msgspec.UNSET

    def __post_init__(self) -> None:
        if all(field is msgspec.UNSET for field in (self.recipient, self.waybill_number, self.comment)):
            msg = "At least one field must be provided for update"
            raise ValueError(msg)

        if isinstance(self.recipient, str):
            self.recipient = validate_title(self.recipient, max_length=RECIPIENT_MAX_LENGTH)

        if isinstance(self.waybill_number, str):
            self.waybill_number = validate_title(self.waybill_number, max_length=WAYBILL_NUMBER_MAX_LENGTH)

        if isinstance(self.comment, str):
            self.comment = validate_description(self.comment)


class BatchShipmentVoid(CamelizedBaseStruct):
    """Void a shipment; it stays in the list and its KG units may be shipped again."""

    reason: VoidReason

    def __post_init__(self) -> None:
        self.reason = validate_title(self.reason, max_length=VOID_REASON_MAX_LENGTH)


class BatchShipmentItem(CamelizedBaseStruct):
    dev_eui: str
    short_id: str
    created_at: datetime


class BatchShipmentUnitsAdd(CamelizedBaseStruct):
    """Add KG units of the batch to an open shipment; each code is added or rejected on its own."""

    codes: UnitCodes


class BatchShipmentUnitRejection(StrEnum):
    """Why a KG unit was not added to a shipment."""

    NOT_FOUND = "batch_shipment_kg_not_found"
    OTHER_BATCH = "batch_shipment_kg_other_batch"
    ALREADY_ADDED = "batch_shipment_kg_already_added"
    IN_OTHER_SHIPMENT = "batch_shipment_kg_in_other_shipment"
    NOT_PACKED = "batch_shipment_kg_not_packed"


class BatchShipmentUnitRejected(CamelizedBaseStruct):
    code: str
    """The code as sent."""
    reason: BatchShipmentUnitRejection


class BatchShipmentUnitsAdded(CamelizedBaseStruct):
    added: list[str]
    """DevEUIs of the units added by this request."""
    rejected: list[BatchShipmentUnitRejected]
    shipment: BatchShipment
