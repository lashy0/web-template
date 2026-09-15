"""Compatibility spelling for the quality-owned repository."""

from app.contexts.quality.verification.repository import VerificationRepository

VerificationStepRepository = VerificationRepository

__all__ = ["VerificationStepRepository"]
