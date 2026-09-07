from __future__ import annotations

from datetime import datetime, timedelta

from app.modules.kg.models import KgStatus
from app.modules.pak.models import PakDevice

from ..exceptions import (
    VerificationSessionNotFoundError,
    VerificationSessionNotRunningError,
    VerificationStepOutOfRangeError,
)
from ..models import (
    VerificationSession,
    VerificationSessionStatus,
    VerificationStep,
    VerificationStepStatus,
)


def ensure_session_owned_by_pak(
    verification_session: VerificationSession,
    pak: PakDevice,
) -> None:
    if verification_session.pak_id != pak.id:
        # Do not expose another PAK's session
        raise VerificationSessionNotFoundError


def ensure_session_running(verification_session: VerificationSession) -> None:
    if verification_session.status != VerificationSessionStatus.RUNNING:
        raise VerificationSessionNotRunningError


def ensure_step_in_range(
    verification_session: VerificationSession,
    step_no: int,
) -> None:
    if not (1 <= step_no <= verification_session.total_steps):
        raise VerificationStepOutOfRangeError


def is_reopen_stale(
    verification_session: VerificationSession,
    *,
    now: datetime,
    reopen_inactivity: timedelta,
) -> bool:
    return now - verification_session.last_activity_at >= reopen_inactivity


def kg_status_after_completion(status: VerificationSessionStatus) -> KgStatus:
    if status == VerificationSessionStatus.PASSED:
        return KgStatus.READY_FOR_PACKING

    if status == VerificationSessionStatus.FAILED:
        return KgStatus.TEST_FAILED

    if status == VerificationSessionStatus.ABORTED:
        return KgStatus.READY_FOR_RETEST

    raise ValueError("Unsupported verification completion status")


def same_step_result(
    step: VerificationStep,
    *,
    status: VerificationStepStatus,
    measurement_value: float | None,
    measurement_min_value: float | None,
    measurement_max_value: float | None,
    measurement_unit: str | None,
) -> bool:
    return (
        step.status == status
        and step.measurement_value == measurement_value
        and step.measurement_min_value == measurement_min_value
        and step.measurement_max_value == measurement_max_value
        and step.measurement_unit == measurement_unit
    )
