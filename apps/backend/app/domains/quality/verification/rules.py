from datetime import datetime, timedelta

from .contracts import VerificationPakPort
from .exceptions import (
    VerificationSessionNotFoundError,
    VerificationSessionNotRunningError,
    VerificationStepOutOfRangeError,
)
from .model import (
    VerificationSession,
    VerificationSessionStatus,
    VerificationStep,
    VerificationStepStatus,
)


def ensure_session_owned_by_pak(item: VerificationSession, pak: VerificationPakPort) -> None:
    if item.pak_id != pak.id:
        raise VerificationSessionNotFoundError


def ensure_session_running(item: VerificationSession) -> None:
    if item.status != VerificationSessionStatus.RUNNING:
        raise VerificationSessionNotRunningError


def ensure_step_in_range(item: VerificationSession, step_no: int) -> None:
    if not 1 <= step_no <= item.total_steps:
        raise VerificationStepOutOfRangeError


def is_reopen_stale(
    item: VerificationSession, *, now: datetime, reopen_inactivity: timedelta
) -> bool:
    return now - item.last_activity_at >= reopen_inactivity


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
