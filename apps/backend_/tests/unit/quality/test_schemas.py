import msgspec
import pytest

from app.domain.quality.schemas import (
    DefectGroupCreate,
    DefectTypeCreate,
    DefectTypeUpdate,
    VerificationSessionOpen,
    VerificationStepComplete,
    VerificationStepStart,
)
from app.lib.lorawan import InvalidDevEuiError
from app.lib.validation import ValidationError

pytestmark = pytest.mark.unit


def test_defect_group_create_strips_code_and_name() -> None:
    data = DefectGroupCreate(code="  RF  ", name="  Radio  ")

    assert (data.code, data.name) == ("RF", "Radio")


def test_defect_group_code_cannot_contain_whitespace() -> None:
    with pytest.raises(ValidationError):
        DefectGroupCreate(code="RF LOW", name="Radio")


def test_defect_group_code_is_limited_to_32_characters() -> None:
    with pytest.raises(ValidationError):
        DefectGroupCreate(code="R" * 33, name="Radio")


def test_defect_type_code_is_limited_to_64_characters() -> None:
    with pytest.raises(ValidationError):
        msgspec.convert(
            {"groupId": "0192f0c6-0000-7000-8000-000000000000", "code": "R" * 65, "name": "Low", "description": "x"},
            DefectTypeCreate,
        )


def test_defect_type_requires_description() -> None:
    with pytest.raises(ValidationError):
        msgspec.convert(
            {"groupId": "0192f0c6-0000-7000-8000-000000000000", "code": "LOW", "name": "Low", "description": "  "},
            DefectTypeCreate,
        )


def test_defect_type_update_requires_a_field() -> None:
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({}, DefectTypeUpdate)


def test_defect_type_update_can_clear_optional_guidance() -> None:
    data = msgspec.convert({"possibleCause": None}, DefectTypeUpdate)

    assert data.to_dict() == {"possible_cause": None}


def test_verification_session_open_normalizes_dev_eui() -> None:
    data = VerificationSessionOpen(dev_eui=" A1B2C3D4E5000001 ", slot_no=1, firmware_version=" 1.0 ", total_steps=1)

    assert (data.dev_eui, data.firmware_version) == ("a1b2c3d4e5000001", "1.0")


def test_verification_session_open_rejects_invalid_dev_eui() -> None:
    with pytest.raises(InvalidDevEuiError):
        VerificationSessionOpen(dev_eui="a1b2", slot_no=1, firmware_version="1.0", total_steps=1)


def test_verification_step_start_rejects_blank_check_name() -> None:
    with pytest.raises(ValidationError):
        VerificationStepStart(step_no=1, check_name="  ", check_label="RF power", defect_group_code="RF")


def test_verification_step_complete_rejects_minimum_above_maximum() -> None:
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"status": "passed", "measurementMin": 2, "measurementMax": 1}, VerificationStepComplete)


def test_verification_step_complete_treats_blank_unit_as_none() -> None:
    data = msgspec.convert({"status": "passed", "measurementValue": 1, "measurementUnit": " "}, VerificationStepComplete)

    assert data.measurement_unit is None


def test_verification_step_complete_treats_zero_limits_as_none() -> None:
    data = msgspec.convert(
        {"status": "passed", "measurementValue": -3, "measurementMin": 0.0, "measurementMax": 0.0},
        VerificationStepComplete,
    )

    assert (data.measurement_min, data.measurement_max) == (None, None)


def test_verification_step_complete_keeps_limits_starting_at_zero() -> None:
    data = msgspec.convert(
        {"status": "passed", "measurementValue": 5, "measurementMin": 0.0, "measurementMax": 500.0},
        VerificationStepComplete,
    )

    assert (data.measurement_min, data.measurement_max) == (0.0, 500.0)


def test_verification_step_complete_accepts_only_final_results() -> None:
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"status": "running"}, VerificationStepComplete)
