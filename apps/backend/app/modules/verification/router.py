"""Compatibility import path for the quality-owned router."""

from app.contexts.quality.verification.router import (
    machine_router,
    router,
)

__all__ = ["machine_router", "router"]
