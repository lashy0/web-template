from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.components.keygen.types import ActivationType, LoRaWanVersion
from app.contexts.production.batches.commands import (
    AssignProductionOrder,
    CompleteBatch,
    CreateBatch,
    SetBatchArchived,
    UpdateBatch,
)
from app.contexts.production.batches.model import Batch, BatchLoRaWanConfig, BatchStatus
from app.contexts.production.exceptions import (
    BatchArchivedError,
    BatchEditNotAllowedError,
    BatchPreparationNotReadyError,
)
from app.contexts.production.kg.commands.allocate_for_batch import BatchAllocation
from app.contexts.production.preparation.model import (
    BatchKeyGenerationJob,
    BatchKeyGenerationStatus,
)
from app.shared.security import CurrentPrincipal, Role
from app.worker.preparation_dispatcher import CeleryWorkDispatcher


def _actor(role: Role = Role.ADMINISTRATOR) -> CurrentPrincipal:
    return CurrentPrincipal(uuid4(), uuid4(), uuid4(), role, "Manager", "manager")


def _batch(*, actor: CurrentPrincipal, archived: bool = False) -> Batch:
    now = datetime.now(UTC)
    return Batch(
        id=uuid4(),
        name="September",
        description="run",
        dev_eui_prefix="a1b2c3d4e5",
        planned_qty=10,
        day_plan_qty=2,
        status=BatchStatus.IN_PRODUCTION,
        created_by_user_id=actor.user_id,
        created_at=now,
        updated_at=now,
        archived_at=now if archived else None,
    )


class _Repository:
    def __init__(self, batch: Batch) -> None:
        self.batch = batch

    async def get(self, batch_id, *, for_update=False):  # type: ignore[no-untyped-def]
        return self.batch if batch_id == self.batch.id else None

    async def update(self, batch, *, updates):  # type: ignore[no-untyped-def]
        for key, value in updates.items():
            setattr(batch, key, value)
        return batch

    async def complete(self, batch, *, completed_at):  # type: ignore[no-untyped-def]
        batch.status = BatchStatus.COMPLETED
        batch.completed_at = completed_at
        return batch

    async def set_archived(self, batch, *, archived_at):  # type: ignore[no-untyped-def]
        batch.archived_at = archived_at
        return batch


class _TransactionSession:
    def __init__(self, events: list[str]) -> None:
        self._events = events
        self.flush = AsyncMock()

    def begin(self) -> _TransactionSession:
        return self

    async def __aenter__(self) -> _TransactionSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        self._events.append("committed")


class _TransactionSessionFactory:
    def __init__(self, events: list[str]) -> None:
        self._session = _TransactionSession(events)

    def __call__(self) -> _TransactionSession:
        return self._session


@pytest.mark.unit
async def test_archived_batch_cannot_be_updated() -> None:
    actor = _actor()
    batch = _batch(actor=actor, archived=True)
    audit = SimpleNamespace(record=AsyncMock())

    with pytest.raises(BatchArchivedError):
        await UpdateBatch(_Repository(batch), audit).execute(
            actor=actor, batch_id=batch.id, updates={"name": "Changed"}
        )

    audit.record.assert_not_awaited()


@pytest.mark.unit
async def test_manager_cannot_update_someone_elses_batch_inside_edit_window() -> None:
    owner, other_manager = _actor(Role.MANAGER), _actor(Role.MANAGER)
    batch = _batch(actor=owner)

    with pytest.raises(BatchEditNotAllowedError):
        await UpdateBatch(_Repository(batch), SimpleNamespace(record=AsyncMock())).execute(
            actor=other_manager, batch_id=batch.id, updates={"name": "Changed"}
        )


@pytest.mark.unit
async def test_complete_requires_ready_preparation_and_audits_completion() -> None:
    actor = _actor()
    batch = _batch(actor=actor)
    preparation = SimpleNamespace(
        get=AsyncMock(
            return_value=BatchKeyGenerationJob(
                batch_id=batch.id, status=BatchKeyGenerationStatus.GENERATING, progress=50
            )
        )
    )
    audit = SimpleNamespace(record=AsyncMock())

    with pytest.raises(BatchPreparationNotReadyError):
        await CompleteBatch(_Repository(batch), preparation, audit).execute(
            actor=actor, batch_id=batch.id
        )

    preparation.get.return_value.status = BatchKeyGenerationStatus.READY
    completed = await CompleteBatch(_Repository(batch), preparation, audit).execute(
        actor=actor, batch_id=batch.id
    )

    assert completed.status is BatchStatus.COMPLETED
    assert audit.record.await_args.kwargs["action"] == "batch.completed"


@pytest.mark.unit
async def test_archive_restore_and_order_reassignment_keep_audit_snapshots() -> None:
    actor = _actor()
    batch = _batch(actor=actor)
    repository = _Repository(batch)
    audit = SimpleNamespace(record=AsyncMock())
    archived = await SetBatchArchived(repository, audit).execute(
        actor=actor, batch_id=batch.id, archived=True
    )
    archived_at = archived.archived_at
    restored = await SetBatchArchived(repository, audit).execute(
        actor=actor, batch_id=batch.id, archived=False
    )
    order = uuid4()
    orders = SimpleNamespace(ensure_assignable=AsyncMock())
    attached = await AssignProductionOrder(repository, orders, audit).execute(
        actor=actor, batch_id=batch.id, production_order_id=order
    )
    attached_order_id = attached.production_order_id
    detached = await AssignProductionOrder(repository, orders, audit).execute(
        actor=actor, batch_id=batch.id, production_order_id=None
    )

    assert archived_at is not None
    assert restored.archived_at is None
    assert attached_order_id == order
    assert detached.production_order_id is None
    assert orders.ensure_assignable.await_count == 1


@pytest.mark.unit
async def test_create_uses_allocation_and_creates_initial_preparation_job(monkeypatch) -> None:
    actor = _actor()
    batch = _batch(actor=actor)
    batch.lorawan_config = BatchLoRaWanConfig(
        activation_type=ActivationType.OTAA,
        lorawan_version=LoRaWanVersion.V1_1,
        join_eui="0123456789abcdef",
    )
    repository = SimpleNamespace(create=AsyncMock(return_value=batch))
    prefix = SimpleNamespace(prefix=batch.dev_eui_prefix, short_code="kg")
    allocation = BatchAllocation(prefix=prefix, dev_euis=["a1b2c3d4e5000001"])
    monkeypatch.setattr(
        "app.contexts.production.batches.commands.create.AllocateForBatch.execute",
        AsyncMock(return_value=allocation),
    )
    kg_repository = SimpleNamespace(
        get_version=AsyncMock(), create_many=AsyncMock(return_value=[SimpleNamespace()])
    )
    preparation = SimpleNamespace(create_initial_job=AsyncMock())
    audit = SimpleNamespace(record=AsyncMock())

    created = await CreateBatch(
        repository,
        kg_repository,
        preparation,
        SimpleNamespace(ensure_assignable=AsyncMock()),
        audit,
    ).execute(
        actor=actor,
        name=batch.name,
        description=batch.description,
        dev_eui_prefix=batch.dev_eui_prefix,
        planned_qty=1,
        day_plan_qty=1,
        activation_type=ActivationType.OTAA,
        lorawan_version=LoRaWanVersion.V1_1,
    )

    assert created is batch
    preparation.create_initial_job.assert_awaited_once_with(batch.id)
    assert audit.record.await_args.kwargs["action"] == "batch.created"


@pytest.mark.unit
async def test_dispatch_failure_marks_initial_preparation_job_failed(monkeypatch) -> None:
    batch_id = uuid4()
    monkeypatch.setattr(
        "app.worker.preparation_dispatcher.celery_app.send_task",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("broker unavailable")),
    )
    mark_failed = AsyncMock(return_value=(BatchKeyGenerationStatus.FAILED, 0))
    monkeypatch.setattr("app.worker.preparation_dispatcher.mark_failed", mark_failed)
    publish = MagicMock()
    notifier = SimpleNamespace(publish=publish)

    await CeleryWorkDispatcher(_TransactionSessionFactory([]), notifier).dispatch_after_commit(
        batch_id
    )

    mark_failed.assert_awaited_once()
    publish.assert_called_once_with(batch_id, BatchKeyGenerationStatus.FAILED, 0)
