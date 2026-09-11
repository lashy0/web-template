from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.config import get_settings
from app.infrastructure.database.session import create_database
from app.modules.batch.services.key_generation import BatchKeyGenerationService
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
            await BatchKeyGenerationService(
                database.session_factory,
                encryption_key=settings.LORAWAN_CREDENTIALS_ENCRYPTION_KEY,
            ).generate(UUID(batch_id))

        finally:
            await database.close()

    asyncio.run(run())
