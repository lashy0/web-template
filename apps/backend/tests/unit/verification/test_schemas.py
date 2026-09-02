import pytest
from pydantic import ValidationError

from app.modules.verification.schemas import (
    CompleteVerificationSessionRequest,
    CompleteVerificationStepRequest,
    OpenVerificationSessionRequest,
    StartVerificationStepRequest,
)


@pytest.mark.unit
def test_open_session_normalizes_kg_and_firmware_version() -> None:
    payload = OpenVerificationSessionRequest.model_validate(
        {
            "kg_dev_eui": " A1B2C3D4E5F60708 ",
            "slot_no": 1,
            "firmware_version": " 1.2.3 ",
            "total_steps": 2,
        }
    )

    assert payload.kg_dev_eui == "a1b2c3d4e5f60708"
    assert payload.firmware_version == "1.2.3"


@pytest.mark.unit
def test_start_step_rejects_text_that_becomes_empty_after_normalization() -> None:
    with pytest.raises(ValidationError):
        StartVerificationStepRequest.model_validate(
            {
                "step_no": 1,
                "test_name": "   ",
                "test_label": "Voltage",
                "error_group_code": "POWER",
            }
        )


@pytest.mark.unit
def test_complete_step_rejects_non_final_status_and_invalid_measurement_range() -> None:
    with pytest.raises(ValidationError, match="PASSED or FAILED"):
        CompleteVerificationStepRequest.model_validate({"status": "RUNNING"})

    with pytest.raises(ValidationError, match="minimum value"):
        CompleteVerificationStepRequest.model_validate(
            {
                "status": "PASSED",
                "measurement_min_value": 2.0,
                "measurement_max_value": 1.0,
            }
        )


@pytest.mark.unit
def test_complete_session_rejects_non_final_status() -> None:
    with pytest.raises(ValidationError, match="PASSED, FAILED or ABORTED"):
        CompleteVerificationSessionRequest.model_validate({"status": "RUNNING"})
