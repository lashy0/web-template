"""Compatibility export for the migrated production-order ORM model."""

from app.contexts.production.production_orders.model import ProductionOrder

__all__ = ["ProductionOrder"]
