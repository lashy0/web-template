"""Compatibility alias; prefix SQL belongs to production.kg.repository."""

from app.contexts.production.kg.repository import KgRepository as KgDevEuiPrefixRepository

__all__ = ["KgDevEuiPrefixRepository"]
