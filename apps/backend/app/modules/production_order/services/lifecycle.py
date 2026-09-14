"""Compatibility export for the migrated authorization rule."""

from app.contexts.production.production_orders.rules import ensure_management_allowed

__all__ = ["ensure_management_allowed"]
