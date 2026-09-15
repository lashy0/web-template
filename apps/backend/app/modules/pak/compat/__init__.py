"""Compatibility adapters for unmigrated PAK ownership."""

from .verification import LegacyVerificationPakAdapter

__all__ = ["LegacyVerificationPakAdapter"]
"""Legacy compatibility namespace; PAK verification adapter has moved to equipment."""
