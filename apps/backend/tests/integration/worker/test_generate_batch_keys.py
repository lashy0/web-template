import base64
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from pytest_mock import MockerFixture
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.components.keygen.types import ActivationType, LoRaWanVersion
from app.domains.production.batches.repository import BatchRepository
from app.domains.production.kg.model import KgDevEuiPrefix, LoRaWanCredentials
from app.domains.production.kg.repository import KgRepository
from app.domains.production.preparation.commands.process_chunk import KEY_GENERATION_CHUNK_SIZE
from app.domains.production.preparation.commands.process_job import ProcessJob
from app.domains.production.preparation.model import BatchKeyGenerationStatus
from app.domains.production.preparation.repository import PreparationRepository
from app.infrastructure.post_commit import preparation_effect_executor


def _encryption_key() -> SecretStr:
    return SecretStr(base64.urlsafe_b64encode(bytes(range(32))).decode("ascii"))


async def _create_batch(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    quantity: int,
) -> UUID:
    prefix = uuid4().hex[:10]
    async with session_factory() as session, session.begin():
        session.add(KgDevEuiPrefix(prefix=prefix, short_code=uuid4().hex[:8]))
        await session.flush()
        batch = await BatchRepository(session).create(
            dev_eui_prefix=prefix,
            name="Credentials batch",
            description=None,
            planned_qty=quantity,
            day_plan_qty=quantity,
            created_by_user_id=None,
            activation_type=ActivationType.OTAA,
            lorawan_version=LoRaWanVersion.V1_1,
            join_eui=uuid4().hex[:16],
        )
        await KgRepository(session).create_many(
            batch_id=batch.id,
            dev_euis=[f"{prefix}{index:06x}" for index in range(quantity)],
            short_code="kg",
        )
        await PreparationRepository(session).create_initial_job(batch.id)

        return batch.id


async def _preparation_status(
    session_factory: async_sessionmaker[AsyncSession], batch_id: UUID
) -> BatchKeyGenerationStatus:
    async with session_factory() as session:
        job = await PreparationRepository(session).get(batch_id)
        assert job is not None
        return job.status


@pytest.mark.integration
async def test_task_generates_keys_transitions_status_and_is_idempotent(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    batch_id = await _create_batch(database_session_factory, quantity=2)
    events: list[tuple[UUID, BatchKeyGenerationStatus, int]] = []

    def publisher(
        event_batch_id: UUID, event_status: BatchKeyGenerationStatus, progress: int
    ) -> None:
        events.append((event_batch_id, event_status, progress))

    await ProcessJob(
        database_session_factory,
        encryption_key=_encryption_key(),
        effect_executor=preparation_effect_executor(
            type("Notifier", (), {"publish": staticmethod(publisher)})()
        ),
    ).execute(batch_id)

    assert (
        await _preparation_status(database_session_factory, batch_id)
        is BatchKeyGenerationStatus.READY
    )
    assert events == [
        (batch_id, BatchKeyGenerationStatus.GENERATING, 0),
        (batch_id, BatchKeyGenerationStatus.GENERATING, 100),
        (batch_id, BatchKeyGenerationStatus.READY, 100),
    ]

    async with database_session_factory() as session:
        before = list(await session.scalars(select(LoRaWanCredentials.encrypted_data)))

    await ProcessJob(
        database_session_factory,
        encryption_key=_encryption_key(),
        effect_executor=preparation_effect_executor(
            type("Notifier", (), {"publish": staticmethod(publisher)})()
        ),
    ).execute(batch_id)

    async with database_session_factory() as session:
        after = list(await session.scalars(select(LoRaWanCredentials.encrypted_data)))

    assert after == before
    assert events == [
        (batch_id, BatchKeyGenerationStatus.GENERATING, 0),
        (batch_id, BatchKeyGenerationStatus.GENERATING, 100),
        (batch_id, BatchKeyGenerationStatus.READY, 100),
    ]


@pytest.mark.integration
async def test_task_marks_batch_failed_and_publishes_event(
    database_session_factory: async_sessionmaker[AsyncSession],
    mocker: MockerFixture,
) -> None:
    batch_id = await _create_batch(database_session_factory, quantity=1)
    events: list[BatchKeyGenerationStatus] = []
    mocker.patch(
        "app.domains.production.preparation.commands.process_chunk.generate_credentials",
        side_effect=RuntimeError("generator failed"),
    )

    with pytest.raises(RuntimeError, match="generator failed"):
        await ProcessJob(
            database_session_factory,
            encryption_key=_encryption_key(),
            effect_executor=preparation_effect_executor(
                type(
                    "Notifier",
                    (),
                    {
                        "publish": staticmethod(
                            lambda _, event_status, __: events.append(event_status)
                        )
                    },
                )()
            ),
        ).execute(batch_id)

    assert (
        await _preparation_status(database_session_factory, batch_id)
        is BatchKeyGenerationStatus.FAILED
    )
    assert events == [BatchKeyGenerationStatus.GENERATING, BatchKeyGenerationStatus.FAILED]


@pytest.mark.integration
async def test_task_processes_more_than_one_thousand_units_in_chunks(
    database_session_factory: async_sessionmaker[AsyncSession],
    mocker: MockerFixture,
) -> None:
    batch_id = await _create_batch(database_session_factory, quantity=1001)
    list_missing = mocker.spy(KgRepository, "select_without_credentials_for_batch")

    await ProcessJob(
        database_session_factory,
        encryption_key=_encryption_key(),
        effect_executor=preparation_effect_executor(
            type("Notifier", (), {"publish": staticmethod(lambda *_: None)})()
        ),
    ).execute(batch_id)

    assert (
        await _preparation_status(database_session_factory, batch_id)
        is BatchKeyGenerationStatus.READY
    )
    assert list_missing.call_count == 4
    assert all(
        call.kwargs["limit"] == KEY_GENERATION_CHUNK_SIZE for call in list_missing.call_args_list
    )
    async with database_session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(LoRaWanCredentials)) == 1001
