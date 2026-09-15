"""Compatibility spelling for the quality-owned repository."""

from app.contexts.quality.verification.repository import VerificationRepository

VerificationSessionRepository = VerificationRepository

__all__ = ["VerificationSessionRepository"]
