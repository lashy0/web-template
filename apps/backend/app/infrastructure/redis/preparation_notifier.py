from uuid import UUID

from app.contexts.production.preparation.model import BatchKeyGenerationStatus
from app.contexts.production.preparation.notifier import ProgressNotifier

from .publisher import publish_event


class RedisProgressNotifier(ProgressNotifier):
    """Redis/SSE outbound adapter for committed preparation state."""

    def publish(self, batch_id: UUID, status: BatchKeyGenerationStatus, progress: int) -> None:
        publish_event(
            type="batch.preparation_updated",
            data={"batch_id": str(batch_id), "status": status.value, "progress": progress},
        )
