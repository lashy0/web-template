from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.kg.schemas import DevEui
from app.modules.verification.models import (
    VerificationSessionStatus,
    VerificationStepStatus,
)


class OpenVerificationSessionRequest(BaseModel):
    kg_dev_eui: DevEui
    slot_no: int = Field(gt=0)
    firmware_version: str = Field(min_length=1, max_length=64)
    total_steps: int = Field(gt=0)

    @field_validator("firmware_version", mode="before")
    @classmethod
    def normalize_firmware_version(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value


class StartVerificationStepRequest(BaseModel):
    step_no: int = Field(gt=0)
    test_name: str = Field(min_length=1, max_length=128)
    test_label: str = Field(min_length=1, max_length=255)
    error_group_code: str = Field(min_length=1, max_length=32)

    @field_validator("test_name", "test_label", "error_group_code", mode="before")
    @classmethod
    def normalize_test_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value


class CompleteVerificationStepRequest(BaseModel):
    status: VerificationStepStatus
    measurement_value: float | None = Field(default=None, allow_inf_nan=False)
    measurement_min_value: float | None = Field(default=None, allow_inf_nan=False)
    measurement_max_value: float | None = Field(default=None, allow_inf_nan=False)
    measurement_unit: str | None = Field(default=None, min_length=1, max_length=32)

    @field_validator("status")
    @classmethod
    def validate_final_status(cls, value: VerificationStepStatus) -> VerificationStepStatus:
        if value not in {
            VerificationStepStatus.PASSED,
            VerificationStepStatus.FAILED,
        }:
            raise ValueError("Completed step status must be PASSED or FAILED")

        return value

    @field_validator("measurement_unit", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value

    @model_validator(mode="after")
    def validate_measurement_range(self) -> "CompleteVerificationStepRequest":
        if (
            self.measurement_min_value is not None
            and self.measurement_max_value is not None
            and self.measurement_min_value > self.measurement_max_value
        ):
            raise ValueError("Measurement minimum value must not exceed maximum value")

        return self


class CompleteVerificationSessionRequest(BaseModel):
    status: VerificationSessionStatus

    @field_validator("status")
    @classmethod
    def validate_final_status(cls, value: VerificationSessionStatus) -> VerificationSessionStatus:
        if value not in {
            VerificationSessionStatus.PASSED,
            VerificationSessionStatus.FAILED,
            VerificationSessionStatus.ABORTED,
        }:
            raise ValueError("Completed session status must be PASSED, FAILED or ABORTED")

        return value
