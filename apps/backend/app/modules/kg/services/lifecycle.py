from collections.abc import Sequence
from uuid import UUID

from ..exceptions import KgCannotBeDeletedError, KgInvalidStateError, KgWrongBatchError
from ..models import KgStatus, KgUnit


def ensure_verification_ready(kg: KgUnit) -> None:
    if kg.status not in {KgStatus.REGISTERED, KgStatus.READY_FOR_RETEST}:
        raise KgInvalidStateError


def ensure_verification_completion_allowed(kg: KgUnit, target: KgStatus) -> None:
    if kg.status != KgStatus.TESTING or target not in {
        KgStatus.READY_FOR_PACKING,
        KgStatus.TEST_FAILED,
        KgStatus.READY_FOR_RETEST,
    }:
        raise KgInvalidStateError


def ensure_can_delete(kg: KgUnit) -> None:
    if kg.status != KgStatus.REGISTERED:
        raise KgCannotBeDeletedError


def ensure_batch_state(units: Sequence[KgUnit], *, batch_id: UUID, status: KgStatus) -> None:
    if any(kg.batch_id != batch_id for kg in units):
        raise KgWrongBatchError

    if any(kg.status != status for kg in units):
        raise KgInvalidStateError
