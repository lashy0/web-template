"""Compatibility route export; implementation is production/kg/router.py."""

from app.contexts.production.kg.router import prefix_router as router

__all__ = ["router"]
