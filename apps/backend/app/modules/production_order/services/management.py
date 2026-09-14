"""Compatibility export for the migrated transaction-owning facade."""

from app.contexts.production.production_orders.service import ProductionOrderManagementService

__all__ = ["ProductionOrderManagementService"]
