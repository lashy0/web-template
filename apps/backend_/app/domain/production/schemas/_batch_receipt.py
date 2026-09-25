from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

import msgspec

from app.domain.production.schemas._batch import UserSummary
from app.domain.production.schemas._common import validate_description, validate_title
from app.lib.schema import CamelizedBaseStruct

ReceiptQty = Annotated[int, msgspec.Meta(ge=1, description="Number of KG units received.")]

VOID_REASON_MAX_LENGTH = 1000


class BatchReceipt(CamelizedBaseStruct):
    id: UUID
    batch_id: UUID
    quantity: int
    comment: str | None
    created_by: UserSummary | None
    voided_at: datetime | None
    void_reason: str | None
    created_at: datetime
    updated_at: datetime


class BatchReceiptCreate(CamelizedBaseStruct):
    """Receive KG units of the batch; all receipts together stay within its planned quantity."""

    quantity: ReceiptQty
    comment: str | None = None

    def __post_init__(self) -> None:
        if self.comment is not None:
            self.comment = validate_description(self.comment)


class BatchReceiptUpdate(CamelizedBaseStruct, omit_defaults=True):
    """Correct a receipt; ``comment: null`` clears the comment."""

    quantity: ReceiptQty | msgspec.UnsetType = msgspec.UNSET
    comment: str | msgspec.UnsetType | None = msgspec.UNSET

    def __post_init__(self) -> None:
        if self.quantity is msgspec.UNSET and self.comment is msgspec.UNSET:
            msg = "At least one field must be provided for update"
            raise ValueError(msg)

        if isinstance(self.comment, str):
            self.comment = validate_description(self.comment)


class BatchReceiptVoid(CamelizedBaseStruct):
    """Void a receipt; it stays in the list and stops counting as received."""

    reason: str

    def __post_init__(self) -> None:
        self.reason = validate_title(self.reason, max_length=VOID_REASON_MAX_LENGTH)
