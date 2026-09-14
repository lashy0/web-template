"""Compatibility import for the receipt repository moved to production."""

from app.contexts.production.receipts.repository import ReceiptRepository

BatchReceiptRepository = ReceiptRepository

__all__ = ["BatchReceiptRepository"]
