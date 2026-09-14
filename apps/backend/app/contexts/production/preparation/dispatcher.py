from typing import Protocol
from uuid import UUID


class WorkDispatcher(Protocol):
    """Outbound port invoked after a CREATING transaction has committed."""

    async def dispatch_after_commit(self, batch_id: UUID) -> None: ...
