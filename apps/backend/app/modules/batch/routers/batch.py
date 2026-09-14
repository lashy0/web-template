"""Compatibility import for the migrated batch HTTP adapter."""

from app.contexts.production.batches.router import router

__all__ = ["router"]
