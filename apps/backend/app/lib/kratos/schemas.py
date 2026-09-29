from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class KratosIdentity:
    id: UUID
    login: str
    is_active: bool
    metadata: dict[str, Any] | None = None
