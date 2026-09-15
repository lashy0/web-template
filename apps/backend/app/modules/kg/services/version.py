"""Deprecated import alias; version commands live in production.kg."""

from app.contexts.production.kg.repository import KgRepository as KgVersionService

__all__ = ["KgVersionService"]
