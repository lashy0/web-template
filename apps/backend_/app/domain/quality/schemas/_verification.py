from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

import msgspec

from app.db.enums import PakDeviceKind, VerificationSessionStatus, VerificationStepStatus
from app.domain.quality.schemas._common import validate_title
from app.lib.lorawan import normalize_dev_eui
from app.lib.schema import CamelizedBaseStruct

CHECK_NAME_MAX_LENGTH = 128
CHECK_LABEL_MAX_LENGTH = 255
DEFECT_GROUP_CODE_MAX_LENGTH = 32
FIRMWARE_VERSION_MAX_LENGTH = 64
MEASUREMENT_UNIT_MAX_LENGTH = 32

SlotNo = Annotated[int, msgspec.Meta(ge=1, description="The PAK slot holding the KG unit.")]
TotalSteps = Annotated[int, msgspec.Meta(ge=1, description="Number of checks the session will run.")]
StepNo = Annotated[int, msgspec.Meta(ge=1, description="Position of the check in the session, from 1.")]


class VerificationSessionPak(CamelizedBaseStruct):
    id: UUID
    code: str


class VerificationStep(CamelizedBaseStruct):
    id: UUID
    step_no: int
    check_id: UUID
    check_name: str
    check_label: str
    defect_group_code: str
    defect_group_id: UUID | None
    status: VerificationStepStatus
    measurement_value: float | None
    measurement_min: float | None
    measurement_max: float | None
    measurement_unit: str | None
    started_at: datetime
    completed_at: datetime | None


class VerificationSession(CamelizedBaseStruct):
    id: UUID
    dev_eui: str
    batch_id: UUID
    pak: VerificationSessionPak
    pak_kind: PakDeviceKind
    slot_no: int
    firmware_version: str
    total_steps: int
    status: VerificationSessionStatus
    started_at: datetime
    last_activity_at: datetime
    completed_at: datetime | None


class VerificationSessionDetail(VerificationSession):
    steps: list[VerificationStep]


class VerificationStepResult(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class VerificationSessionResult(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ABORTED = "aborted"


class VerificationSessionOpen(CamelizedBaseStruct):
    """Start verifying a KG unit in a PAK slot, or resume the session already running there."""

    dev_eui: str
    slot_no: SlotNo
    firmware_version: str
    total_steps: TotalSteps

    def __post_init__(self) -> None:
        self.dev_eui = normalize_dev_eui(self.dev_eui.strip())
        self.firmware_version = validate_title(
            self.firmware_version,
            max_length=FIRMWARE_VERSION_MAX_LENGTH,
        )


class VerificationStepStart(CamelizedBaseStruct):
    """Start a check; repeating the same start is answered with the existing step."""

    step_no: StepNo
    check_name: str
    check_label: str
    defect_group_code: str

    def __post_init__(self) -> None:
        self.check_name = validate_title(self.check_name, max_length=CHECK_NAME_MAX_LENGTH)
        self.check_label = validate_title(self.check_label, max_length=CHECK_LABEL_MAX_LENGTH)
        self.defect_group_code = validate_title(
            self.defect_group_code,
            max_length=DEFECT_GROUP_CODE_MAX_LENGTH,
        )


class VerificationStepComplete(CamelizedBaseStruct):
    """Report the result of a check; repeating the same result is answered with the step.

    A check may have no measurement, or a value without a unit or limits; a
    blank unit means none, and so do limits of 0 to 0, which is how PAKs
    report a check without limits.
    """

    status: VerificationStepResult
    measurement_value: float | None = None
    measurement_min: float | None = None
    measurement_max: float | None = None
    measurement_unit: str | None = None

    def __post_init__(self) -> None:
        if self.measurement_min == 0 and self.measurement_max == 0:
            self.measurement_min = self.measurement_max = None

        if (
            self.measurement_min is not None
            and self.measurement_max is not None
            and self.measurement_min > self.measurement_max
        ):
            msg = "Measurement minimum cannot exceed the maximum"
            raise ValueError(msg)

        if self.measurement_unit is not None and not self.measurement_unit.strip():
            self.measurement_unit = None

        if self.measurement_unit is not None:
            self.measurement_unit = validate_title(
                self.measurement_unit,
                max_length=MEASUREMENT_UNIT_MAX_LENGTH
            )


class VerificationSessionComplete(CamelizedBaseStruct):
    """Finish the session; ``passed`` needs every step passed, ``aborted`` stops a running step."""

    status: VerificationSessionResult
