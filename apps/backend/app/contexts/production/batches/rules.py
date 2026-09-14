from datetime import datetime, timedelta

from app.modules.batch.exceptions import (
    BatchAlreadyCompletedError,
    BatchArchivedError,
    BatchEditNotAllowedError,
    BatchEditWindowExpiredError,
    BatchPreparationNotReadyError,
)
from app.modules.batch.models import BatchKeyGenerationStatus
from app.shared.security import CurrentPrincipal, ForbiddenError, Role

from .model import Batch, BatchStatus

BATCH_EDIT_WINDOW = timedelta(minutes=60)


def ensure_management_allowed(actor: CurrentPrincipal) -> None:
    if actor.role not in (Role.ADMINISTRATOR, Role.MANAGER):
        raise ForbiddenError


def ensure_not_archived(batch: Batch) -> None:
    if batch.archived_at is not None:
        raise BatchArchivedError


def ensure_in_production(
    batch: Batch, *, preparation_status: BatchKeyGenerationStatus | None
) -> None:
    ensure_not_archived(batch)
    if preparation_status is not BatchKeyGenerationStatus.READY:
        raise BatchPreparationNotReadyError
    if batch.status is BatchStatus.COMPLETED:
        raise BatchAlreadyCompletedError


def ensure_batch_edit_allowed(
    batch: Batch,
    *,
    actor: CurrentPrincipal,
    now: datetime,
    edit_window: timedelta = BATCH_EDIT_WINDOW,
) -> None:
    if actor.role == Role.ADMINISTRATOR:
        return
    if batch.created_by_user_id != actor.user_id:
        raise BatchEditNotAllowedError
    if now - batch.created_at > edit_window:
        raise BatchEditWindowExpiredError
