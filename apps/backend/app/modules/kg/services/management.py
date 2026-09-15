"""Deprecated compatibility aliases with no KG business implementation."""

from app.contexts.production.kg.repository import KgRepository

KgManagementService = KgRepository
KgDevEuiPrefixManagementService = KgRepository
KgVersionManagementService = KgRepository

__all__ = [
    "KgDevEuiPrefixManagementService",
    "KgManagementService",
    "KgVersionManagementService",
]
