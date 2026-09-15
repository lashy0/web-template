"""Compatibility re-exports; KG SQL lives in production.kg.repository."""

from app.contexts.production.kg.repository import KgListItem, KgRepository

__all__ = ["KgListItem", "KgRepository"]
