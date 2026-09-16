from uuid import UUID

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.uow import PostCommitExecutor

from .commands.process_job import ProcessJob


async def process_preparation_job(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    encryption_key: SecretStr | None,
    batch_id: UUID,
    effect_executor: PostCommitExecutor,
) -> None:
    await ProcessJob(
        session_factory,
        encryption_key=encryption_key,
        effect_executor=effect_executor,
    ).execute(batch_id)
