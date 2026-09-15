"""Deprecated import alias; prefix commands live in production.kg."""

from app.contexts.production.kg.repository import KgRepository as KgPrefixService

__all__ = ["KgPrefixService"]
