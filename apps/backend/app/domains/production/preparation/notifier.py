from typing import Protocol
from uuid import UUID

from .model import BatchKeyGenerationStatus


class ProgressNotifier(Protocol):
    def publish(self, batch_id: UUID, status: BatchKeyGenerationStatus, progress: int) -> None: ...


class CallableProgressNotifier:
    """Adapter for simple callable-based tests and compatibility callers."""

    def __init__(self, callback: object) -> None:
        self._callback = callback

    def publish(self, batch_id: UUID, status: BatchKeyGenerationStatus, progress: int) -> None:
        callback = self._callback
        if callable(callback):
            callback(batch_id, status, progress)
