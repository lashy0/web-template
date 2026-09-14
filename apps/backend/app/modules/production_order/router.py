"""Compatibility export for the migrated production-order router."""

from app.contexts.production.production_orders.router import router

__all__ = ["router"]
