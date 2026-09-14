"""Compatibility export for the migrated transaction adapter."""

from app.contexts.production.production_orders.service import _transaction as transaction

__all__ = ["transaction"]
