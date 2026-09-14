"""Compatibility export for the migrated caller-UoW facade."""

from app.contexts.production.production_orders.service import ProductionOrderService

__all__ = ["ProductionOrderService"]
