import base64
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from pytest_mock import MockerFixture
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.batch.models import (
    ActivationType,
    BatchKeyGenerationStatus,
    LoRaWanVersion,
)
from app.modules.batch.repositories import BatchRepository
from app.modules.batch.services.key_generation import (
    KEY_GENERATION_CHUNK_SIZE,
    BatchKeyGenerationService,
)
from app.modules.kg.models import KgDevEuiPrefix, LoRaWanCredentials
from app.modules.kg.repositories import KgRepository


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

        return batch.id


async def _batch_status(
    session_factory: async_sessionmaker[AsyncSession], batch_id: UUID
) -> BatchKeyGenerationStatus:
    async with session_factory() as session:
        batch = await BatchRepository(session).get_by_id(batch_id)
        assert batch is not None
        return batch.key_generation_status


@pytest.mark.integration
async def test_task_generates_keys_transitions_status_and_is_idempotent(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    batch_id = await _create_batch(database_session_factory, quantity=2)
    events: list[tuple[UUID, BatchKeyGenerationStatus]] = []

    def publisher(event_batch_id: UUID, event_status: BatchKeyGenerationStatus) -> None:
        events.append((event_batch_id, event_status))

    await BatchKeyGenerationService(
        database_session_factory,
        encryption_key=_encryption_key(),
        publish_status=publisher,
    ).generate(batch_id)

    assert (
        await _batch_status(database_session_factory, batch_id)
        is BatchKeyGenerationStatus.COMPLETED
    )
    assert events == [
        (batch_id, BatchKeyGenerationStatus.RUNNING),
        (batch_id, BatchKeyGenerationStatus.COMPLETED),
    ]

    async with database_session_factory() as session:
        before = list(await session.scalars(select(LoRaWanCredentials.encrypted_data)))

    await BatchKeyGenerationService(
        database_session_factory,
        encryption_key=_encryption_key(),
        publish_status=publisher,
    ).generate(batch_id)

    async with database_session_factory() as session:
        after = list(await session.scalars(select(LoRaWanCredentials.encrypted_data)))

    assert after == before
    assert events == [
        (batch_id, BatchKeyGenerationStatus.RUNNING),
        (batch_id, BatchKeyGenerationStatus.COMPLETED),
    ]


@pytest.mark.integration
async def test_task_marks_batch_failed_and_publishes_event(
    database_session_factory: async_sessionmaker[AsyncSession],
    mocker: MockerFixture,
) -> None:
    batch_id = await _create_batch(database_session_factory, quantity=1)
    events: list[BatchKeyGenerationStatus] = []
    mocker.patch(
        "app.modules.batch.services.key_generation.generate_credentials",
        side_effect=RuntimeError("generator failed"),
    )

    with pytest.raises(RuntimeError, match="generator failed"):
        await BatchKeyGenerationService(
            database_session_factory,
            encryption_key=_encryption_key(),
            publish_status=lambda _, event_status: events.append(event_status),
        ).generate(batch_id)

    assert (
        await _batch_status(database_session_factory, batch_id) is BatchKeyGenerationStatus.FAILED
    )
    assert events == [BatchKeyGenerationStatus.RUNNING, BatchKeyGenerationStatus.FAILED]


@pytest.mark.integration
async def test_task_processes_more_than_one_thousand_units_in_chunks(
    database_session_factory: async_sessionmaker[AsyncSession],
    mocker: MockerFixture,
) -> None:
    batch_id = await _create_batch(database_session_factory, quantity=1001)
    list_missing = mocker.spy(KgRepository, "list_without_credentials_by_batch")

    await BatchKeyGenerationService(
        database_session_factory,
        encryption_key=_encryption_key(),
        publish_status=lambda _, __: None,
    ).generate(batch_id)

    assert (
        await _batch_status(database_session_factory, batch_id)
        is BatchKeyGenerationStatus.COMPLETED
    )
    assert list_missing.call_count == 4
    assert all(
        call.kwargs["limit"] == KEY_GENERATION_CHUNK_SIZE for call in list_missing.call_args_list
    )
    async with database_session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(LoRaWanCredentials)) == 1001
