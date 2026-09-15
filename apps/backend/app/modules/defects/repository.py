"""Compatibility repository exports; persistence is owned by quality.defects."""

from app.contexts.quality.defects.repository import DefectGroupRepository, DefectTypeRepository

__all__ = ["DefectGroupRepository", "DefectTypeRepository"]
