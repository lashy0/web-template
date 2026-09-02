from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.defects.schemas import (
    CreateDefectGroupRequest,
    CreateDefectTypeRequest,
    UpdateDefectTypeRequest,
)


@pytest.mark.unit
def test_create_group_normalizes_code_and_empty_description() -> None:
    payload = CreateDefectGroupRequest.model_validate(
        {
            "code": "  POWER  ",
            "name": "  Power supply  ",
            "description": "   ",
        }
    )

    assert payload.code == "POWER"
    assert payload.name == "Power supply"
    assert payload.description is None


@pytest.mark.unit
def test_create_type_normalizes_text_fields() -> None:
    group_id = uuid4()

    payload = CreateDefectTypeRequest.model_validate(
        {
            "group_id": group_id,
            "code": "  VOLTAGE_LOW  ",
            "name": "  Low voltage  ",
            "description": "  Voltage is below the acceptable range.  ",
            "possible_cause": "  Loose cable  ",
            "engineer_action": "   ",
        }
    )

    assert payload.group_id == group_id
    assert payload.code == "VOLTAGE_LOW"
    assert payload.name == "Low voltage"
    assert payload.description == "Voltage is below the acceptable range."
    assert payload.possible_cause == "Loose cable"
    assert payload.engineer_action is None


@pytest.mark.unit
def test_defect_code_and_required_text_cannot_be_blank_after_normalization() -> None:
    with pytest.raises(ValidationError):
        CreateDefectGroupRequest.model_validate(
            {"code": "  ", "name": "Power", "description": None}
        )

    with pytest.raises(ValidationError):
        UpdateDefectTypeRequest.model_validate({"description": "  "})
