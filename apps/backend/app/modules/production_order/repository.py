"""Compatibility export for the migrated production-order repository."""

from app.contexts.production.production_orders.repository import ProductionOrderRepository

__all__ = ["ProductionOrderRepository"]
