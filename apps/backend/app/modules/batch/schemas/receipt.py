"""Compatibility exports for schemas moved to production.receipts."""

from app.contexts.production.receipts.schemas import (
    BatchReceiptListResponse,
    BatchReceiptResponse,
    CreateBatchReceiptRequest,
    UpdateBatchReceiptRequest,
    VoidBatchReceiptRequest,
)

__all__ = [
    "BatchReceiptListResponse",
    "BatchReceiptResponse",
    "CreateBatchReceiptRequest",
    "UpdateBatchReceiptRequest",
    "VoidBatchReceiptRequest",
]
