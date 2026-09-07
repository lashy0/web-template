from datetime import UTC, datetime, timedelta

import pytest

from app.modules.verification.exceptions import (
    VerificationSessionNotFoundError,
    VerificationStepOutOfRangeError,
)
from app.modules.verification.services import VerificationManagementService, lifecycle
from tests.unit.verification.test_service import _pak, _SessionFactory, _verification_session

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("reopen,ttl", [(0, 120), (60, 0), (120, 120), (121, 120)])
def test_invalid_timeout_configuration_is_rejected(reopen, ttl):
    with pytest.raises(ValueError):
        VerificationManagementService(
            _SessionFactory(), reopen_inactivity_minutes=reopen, session_ttl_minutes=ttl
        )


def test_reopen_boundary_is_inclusive():
    now = datetime.now(UTC)
    run = _verification_session(_pak(), last_activity_at=now - timedelta(minutes=60))
    assert lifecycle.is_reopen_stale(run, now=now, reopen_inactivity=timedelta(minutes=60))
    assert not lifecycle.is_reopen_stale(
        run, now=now - timedelta(microseconds=1), reopen_inactivity=timedelta(minutes=60)
    )


def test_session_is_hidden_from_another_pak():
    with pytest.raises(VerificationSessionNotFoundError):
        lifecycle.ensure_session_owned_by_pak(_verification_session(_pak()), _pak())


@pytest.mark.parametrize("step_no", [0, -1, 3])
def test_step_must_be_in_declared_range(step_no):
    with pytest.raises(VerificationStepOutOfRangeError):
        lifecycle.ensure_step_in_range(_verification_session(_pak(), total_steps=2), step_no)
