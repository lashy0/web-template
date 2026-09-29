"""System domain schemas."""

from app.domain.system.schemas._health import SystemHealth
from app.domain.system.schemas._version import SystemVersion

__all__ = [
    "SystemHealth",
    "SystemVersion",
]
