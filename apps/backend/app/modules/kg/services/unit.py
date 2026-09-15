"""Deprecated import alias; callers use production.kg repository/commands."""

from app.contexts.production.kg.repository import KgRepository as KgService

__all__ = ["KgService"]
