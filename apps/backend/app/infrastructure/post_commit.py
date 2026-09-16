"""In-process post-commit delivery adapter.

The mapping is intentionally a composition concern.  Replacing this adapter
with an outbox writer leaves commands registering the same effect objects.
"""

from collections.abc import Awaitable, Callable, Mapping

from app.domains.production.preparation.dispatcher import WorkDispatcher
from app.domains.production.preparation.effects import (
    DispatchPreparation,
    PublishPreparationProgress,
)
from app.domains.production.preparation.notifier import ProgressNotifier

EffectHandler = Callable[[object], Awaitable[None]]


class InProcessPostCommitExecutor:
    def __init__(self, handlers: Mapping[type[object], EffectHandler]) -> None:
        self._handlers = dict(handlers)

    async def execute(self, effect: object) -> None:
        handler = self._handlers[type(effect)]
        await handler(effect)


def preparation_effect_executor(
    notifier: ProgressNotifier,
    *,
    dispatcher: WorkDispatcher | None = None,
) -> InProcessPostCommitExecutor:
    """Bind preparation effect types to ports at the infrastructure boundary."""

    async def publish(effect: object) -> None:
        progress = effect
        assert isinstance(progress, PublishPreparationProgress)
        notifier.publish(progress.batch_id, progress.status, progress.progress)

    handlers: dict[type[object], EffectHandler] = {PublishPreparationProgress: publish}
    if dispatcher is not None:

        async def dispatch(effect: object) -> None:
            request = effect
            assert isinstance(request, DispatchPreparation)
            await dispatcher.dispatch(request.batch_id)

        handlers[DispatchPreparation] = dispatch
    return InProcessPostCommitExecutor(handlers)
