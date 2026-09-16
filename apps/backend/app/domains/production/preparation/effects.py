"""Semantic effects emitted by preparation commands after a successful commit."""

from dataclasses import dataclass
from uuid import UUID

from .model import BatchKeyGenerationStatus


@dataclass(frozen=True, slots=True)
class DispatchPreparation:
    batch_id: UUID


@dataclass(frozen=True, slots=True)
class PublishPreparationProgress:
    batch_id: UUID
    status: BatchKeyGenerationStatus
    progress: int
