from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domains.production.preparation.commands.mark_failed import mark_failed
from app.domains.production.preparation.dispatcher import WorkDispatcher
from app.domains.production.preparation.model import BatchKeyGenerationStatus
from app.domains.production.preparation.notifier import ProgressNotifier
from app.shared.uow import PostCommitExecutor
from app.worker.celery_app import celery_app

GENERATE_BATCH_KEYS_TASK = "app.worker.generate_batch_keys"


class CeleryWorkDispatcher(WorkDispatcher):
    """Celery outbound adapter, including durable dispatch-failure recovery."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        notifier: ProgressNotifier,
        failed_effect_executor: PostCommitExecutor,
    ) -> None:
        self._session_factory = session_factory
        self._notifier = notifier
        self._failed_effect_executor = failed_effect_executor

    async def dispatch(self, batch_id: UUID) -> None:
        try:
            celery_app.send_task(GENERATE_BATCH_KEYS_TASK, args=[str(batch_id)])
        except Exception:
            logger.bind(
                event="batch.preparation_dispatch_failed", batch_id=str(batch_id)
            ).exception("Could not start batch KG preparation")
            await mark_failed(
                self._session_factory,
                batch_id,
                effect_executor=self._failed_effect_executor,
            )
            return
        try:
            self._notifier.publish(batch_id, BatchKeyGenerationStatus.CREATING, 0)
        except Exception:
            logger.bind(
                event="batch.preparation_notification_failed", batch_id=str(batch_id)
            ).exception("Could not publish committed batch preparation creation")
