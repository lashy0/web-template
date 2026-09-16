from typing import Protocol
from uuid import UUID


class WorkDispatcher(Protocol):
    """Outbound port which starts a committed preparation request."""

    async def dispatch(self, batch_id: UUID) -> None: ...
