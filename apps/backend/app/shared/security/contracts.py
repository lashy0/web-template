"""Provider-independent security value types."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Identity:
    """The provider identity projection consumed by application contexts."""

    id: UUID
    login: str
    active: bool
    metadata: dict[str, object] | None = None


__all__ = ["Identity"]
