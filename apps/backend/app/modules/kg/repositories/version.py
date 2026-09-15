"""Compatibility alias; version SQL belongs to production.kg.repository."""

from app.contexts.production.kg.repository import KgRepository as KgVersionRepository

__all__ = ["KgVersionRepository"]
