import pytest
from pydantic import BaseModel, ValidationError

from app.modules.kg.schemas import DevEui


class DevEuiPayload(BaseModel):
    dev_eui: DevEui


@pytest.mark.unit
def test_dev_eui_is_trimmed_and_normalized_to_lowercase() -> None:
    payload = DevEuiPayload.model_validate({"dev_eui": "  A1B2C3D4E5F60708  "})

    assert payload.dev_eui == "a1b2c3d4e5f60708"


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        pytest.param("a1b2c3d4e5f6070", id="too-short"),
        pytest.param("a1b2c3d4e5f607089", id="too-long"),
        pytest.param("a1b2c3d4e5f6070g", id="not-hex"),
        pytest.param(123, id="not-a-string"),
    ],
)
def test_dev_eui_rejects_invalid_values(value: object) -> None:
    with pytest.raises(ValidationError):
        DevEuiPayload.model_validate({"dev_eui": value})
