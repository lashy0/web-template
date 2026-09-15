"""Compatibility exports; mapped defects live in ``contexts.quality.defects``."""

from app.contexts.quality.defects.model import DefectGroup, DefectType

__all__ = ["DefectGroup", "DefectType"]
