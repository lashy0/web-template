from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.config import get_settings
from app.domains.production.preparation.worker_entry import process_preparation_job
from app.infrastructure.database.session import create_database
from app.infrastructure.post_commit import preparation_effect_executor
from app.infrastructure.redis.preparation_notifier import RedisProgressNotifier
from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.ping")  # type: ignore[untyped-decorator]
def ping() -> str:
    return "pong"


@celery_app.task(name="app.worker.generate_batch_keys")  # type: ignore[untyped-decorator]
def generate_batch_keys(batch_id: str) -> None:
    settings = get_settings()

    async def run() -> None:
        database = create_database(settings)

        try:
            await process_preparation_job(
                database.session_factory,
                encryption_key=settings.LORAWAN_CREDENTIALS_ENCRYPTION_KEY,
                batch_id=UUID(batch_id),
                effect_executor=preparation_effect_executor(RedisProgressNotifier()),
            )

        finally:
            await database.close()

    asyncio.run(run())
