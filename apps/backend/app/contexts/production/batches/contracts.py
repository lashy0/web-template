"""Consumer-owned contracts for batch workflows crossing context boundaries."""

from typing import Protocol
from uuid import UUID


class VerificationHistoryPort(Protocol):
    """Only the verification fact that batch deletion needs."""

    async def has_history_for_batch(self, batch_id: UUID) -> bool: ...
