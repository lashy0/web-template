from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domains.quality.verification.exceptions import (
    VerificationSessionNotFoundError,
    VerificationStepOutOfRangeError,
)
from app.domains.quality.verification.model import VerificationSession
from app.domains.quality.verification.rules import (
    ensure_session_owned_by_pak,
    ensure_step_in_range,
    is_reopen_stale,
)


class Pak:
    def __init__(self) -> None:
        self.id = uuid4()
        self.code = "PAK-1"
        self.oauth_client_id = "pak-1"


def session(pak: Pak, *, total_steps: int = 2) -> VerificationSession:
    now = datetime.now(UTC)
    return VerificationSession(
        kg_dev_eui="a1b2c3d4e5f60708",
        pak_id=pak.id,
        slot_no=1,
        firmware_version="1.0",
        total_steps=total_steps,
        started_at=now,
        last_activity_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
def test_stale_reopen_boundary_is_inclusive() -> None:
    pak = Pak()
    item = session(pak)
    now = item.last_activity_at + timedelta(minutes=60)
    assert is_reopen_stale(item, now=now, reopen_inactivity=timedelta(minutes=60))


@pytest.mark.unit
def test_session_is_hidden_from_another_pak() -> None:
    with pytest.raises(VerificationSessionNotFoundError):
        ensure_session_owned_by_pak(session(Pak()), Pak())


@pytest.mark.unit
@pytest.mark.parametrize("step_no", [0, -1, 3])
def test_step_must_be_in_declared_range(step_no: int) -> None:
    with pytest.raises(VerificationStepOutOfRangeError):
        ensure_step_in_range(session(Pak()), step_no)
