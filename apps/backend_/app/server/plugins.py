from __future__ import annotations

from typing import TYPE_CHECKING

from litestar_autowire import AutowireConfig, AutowirePlugin
from litestar_saq import CronJob, QueueConfig, SAQConfig, SAQPlugin

if TYPE_CHECKING:
    from app.config import Settings

autowire = AutowirePlugin(AutowireConfig(domain_packages=["app.domain"]))

TASKS: list[str] = []
"""Dotted paths of the functions a worker runs on request."""

SCHEDULED_TASKS = [
    CronJob(
        function="app.domain.quality.tasks.expire_stale_verification_sessions",
        cron="* * * * *",
        timeout=50,
    ),
]
"""Recurring tasks; SAQ runs each once per schedule however many workers there are."""


def create_task_queue(settings: Settings) -> SAQPlugin:
    """Build the SAQ plugin with one queue named after the Redis prefix.

    The queue name keeps SAQ's keys inside the runtime ACL user's
    ``saq:<prefix>:*`` namespace.
    """
    return SAQPlugin(
        config=SAQConfig(
            use_server_lifespan=settings.queue.workers_in_server,
            queue_configs=[
                QueueConfig(
                    name=settings.redis.prefix,
                    dsn=str(settings.redis.url),
                    tasks=TASKS,
                    scheduled_tasks=SCHEDULED_TASKS,
                    startup=["app.lib.worker.on_startup"],
                    shutdown=["app.lib.worker.on_shutdown"],
                ),
            ],
        ),
    )
