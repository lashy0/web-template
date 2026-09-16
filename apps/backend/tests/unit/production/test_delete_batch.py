from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domains.production.batches.commands.delete import DeleteBatch
from app.domains.production.batches.model import Batch, BatchStatus
from app.domains.production.exceptions import BatchCannotBeDeletedError
from app.domains.production.preparation.effects import PublishPreparationProgress
from app.domains.production.preparation.model import (
    BatchKeyGenerationJob,
    BatchKeyGenerationStatus,
)
from app.shared.security import CurrentPrincipal, Role


def _actor() -> CurrentPrincipal:
    return CurrentPrincipal(uuid4(), uuid4(), uuid4(), Role.ADMINISTRATOR, "Manager", "manager")


def _batch(actor: CurrentPrincipal) -> Batch:
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
    )


class _Transaction:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def __aenter__(self) -> _Transaction:
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        self._events.append("rollback" if exc_type is not None else "commit")


class _Session:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def begin(self) -> _Transaction:
        return _Transaction(self._events)


class _SessionFactory:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def __call__(self) -> _Session:
        return _Session(self._events)


@pytest.fixture
def workflow_parts(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    actor = _actor()
    batch = _batch(actor)
    parts = SimpleNamespace(
        actor=actor,
        batch=batch,
        events=[],
        repository=SimpleNamespace(
            get=AsyncMock(return_value=batch),
            delete=AsyncMock(),
        ),
        receipts=SimpleNamespace(has_receipts=AsyncMock(return_value=False)),
        shipments=SimpleNamespace(has_shipments=AsyncMock(return_value=False)),
        kg=SimpleNamespace(
            has_scrapped_by_batch=AsyncMock(return_value=False),
            delete_registered_for_batch=AsyncMock(),
        ),
        verification=SimpleNamespace(has_history_for_batch=AsyncMock(return_value=False)),
        preparation=SimpleNamespace(
            get=AsyncMock(return_value=None), request_cancellation=AsyncMock()
        ),
        audit=SimpleNamespace(record=AsyncMock()),
    )
    from app.domains.production.batches.commands import delete as command

    monkeypatch.setattr(command, "BatchRepository", lambda session: parts.repository)
    monkeypatch.setattr(command, "ReceiptRepository", lambda session: parts.receipts)
    monkeypatch.setattr(command, "ShipmentRepository", lambda session: parts.shipments)
    monkeypatch.setattr(command, "KgRepository", lambda session: parts.kg)
    monkeypatch.setattr(command, "PreparationRepository", lambda session: parts.preparation)
    monkeypatch.setattr(
        command.TransactionalAuditWriter,
        "from_session",
        MagicMock(return_value=parts.audit),
    )
    return parts


def _workflow(parts: SimpleNamespace, publisher: MagicMock | None = None) -> DeleteBatch:
    publish = publisher or MagicMock()

    class _EffectExecutor:
        async def execute(self, effect: object) -> None:
            assert isinstance(effect, PublishPreparationProgress)
            publish(effect.batch_id, effect.status, effect.progress)

    return DeleteBatch(
        _SessionFactory(parts.events),  # type: ignore[arg-type]
        verification_history=lambda session: parts.verification,
        effect_executor=_EffectExecutor(),
    )


@pytest.mark.unit
@pytest.mark.parametrize("status", [None, BatchKeyGenerationStatus.READY])
async def test_delete_without_job_or_with_ready_job_is_single_transaction(
    workflow_parts: SimpleNamespace, status: BatchKeyGenerationStatus | None
) -> None:
    if status is not None:
        workflow_parts.preparation.get.return_value = BatchKeyGenerationJob(
            batch_id=workflow_parts.batch.id, status=status, progress=100
        )

    await _workflow(workflow_parts).execute(
        actor=workflow_parts.actor, batch_id=workflow_parts.batch.id
    )

    assert workflow_parts.events == ["commit"]
    workflow_parts.kg.delete_registered_for_batch.assert_awaited_once_with(workflow_parts.batch.id)
    workflow_parts.audit.record.assert_awaited_once()
    assert workflow_parts.audit.record.await_args.kwargs["action"] == "batch.deleted"
    workflow_parts.repository.delete.assert_awaited_once_with(workflow_parts.batch)


@pytest.mark.unit
@pytest.mark.parametrize("fact", ["receipts", "shipments", "kg", "verification"])
async def test_delete_rejects_all_persisted_prohibiting_facts(
    workflow_parts: SimpleNamespace, fact: str
) -> None:
    if fact == "receipts":
        workflow_parts.receipts.has_receipts.return_value = True
    elif fact == "shipments":
        workflow_parts.shipments.has_shipments.return_value = True
    elif fact == "kg":
        workflow_parts.kg.has_scrapped_by_batch.return_value = True
    else:
        workflow_parts.verification.has_history_for_batch.return_value = True

    with pytest.raises(BatchCannotBeDeletedError):
        await _workflow(workflow_parts).execute(
            actor=workflow_parts.actor, batch_id=workflow_parts.batch.id
        )

    assert workflow_parts.events == ["rollback"]
    workflow_parts.repository.delete.assert_not_awaited()
    workflow_parts.audit.record.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.parametrize(
    "status",
    [
        BatchKeyGenerationStatus.CREATING,
        BatchKeyGenerationStatus.GENERATING,
        BatchKeyGenerationStatus.FAILED,
        BatchKeyGenerationStatus.CANCELLING,
    ],
)
async def test_non_ready_job_commits_cancelling_then_cleans_up_under_second_lock(
    workflow_parts: SimpleNamespace, status: BatchKeyGenerationStatus
) -> None:
    job = BatchKeyGenerationJob(batch_id=workflow_parts.batch.id, status=status, progress=37)
    workflow_parts.preparation.get.return_value = job
    published = MagicMock(side_effect=lambda *args: workflow_parts.events.append("published"))

    await _workflow(workflow_parts, published).execute(
        actor=workflow_parts.actor, batch_id=workflow_parts.batch.id
    )

    assert workflow_parts.events == ["commit", "published", "commit"]
    workflow_parts.preparation.request_cancellation.assert_awaited_once_with(job)
    published.assert_called_once_with(
        workflow_parts.batch.id, BatchKeyGenerationStatus.CANCELLING, 37
    )
    assert workflow_parts.repository.get.await_args_list[0].kwargs["for_update"] is True
    assert workflow_parts.repository.get.await_args_list[1].kwargs["for_update"] is True
    workflow_parts.kg.delete_registered_for_batch.assert_awaited_once_with(workflow_parts.batch.id)
    assert workflow_parts.audit.record.await_args.kwargs["action"] == "batch.deleted"


@pytest.mark.unit
async def test_notification_failure_does_not_rollback_committed_cancellation(
    workflow_parts: SimpleNamespace,
) -> None:
    workflow_parts.preparation.get.return_value = BatchKeyGenerationJob(
        batch_id=workflow_parts.batch.id,
        status=BatchKeyGenerationStatus.GENERATING,
        progress=20,
    )

    await _workflow(workflow_parts, MagicMock(side_effect=RuntimeError("redis down"))).execute(
        actor=workflow_parts.actor, batch_id=workflow_parts.batch.id
    )

    assert workflow_parts.events == ["commit", "commit"]
    workflow_parts.repository.delete.assert_awaited_once_with(workflow_parts.batch)


@pytest.mark.unit
async def test_cleanup_failure_rolls_back_audit_and_delete_together(
    workflow_parts: SimpleNamespace,
) -> None:
    workflow_parts.preparation.get.return_value = BatchKeyGenerationJob(
        batch_id=workflow_parts.batch.id,
        status=BatchKeyGenerationStatus.GENERATING,
        progress=20,
    )
    workflow_parts.repository.delete.side_effect = RuntimeError("delete failed")

    with pytest.raises(RuntimeError, match="delete failed"):
        await _workflow(workflow_parts).execute(
            actor=workflow_parts.actor, batch_id=workflow_parts.batch.id
        )

    assert workflow_parts.events == ["commit", "rollback"]
    workflow_parts.audit.record.assert_awaited_once()
