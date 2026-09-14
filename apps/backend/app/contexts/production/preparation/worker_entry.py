from uuid import UUID

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .commands.process_job import ProcessJob
from .notifier import ProgressNotifier


async def process_preparation_job(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    encryption_key: SecretStr | None,
    batch_id: UUID,
    notifier: ProgressNotifier,
) -> None:
    await ProcessJob(
        session_factory,
        encryption_key=encryption_key,
        notifier=notifier,
    ).execute(batch_id)
