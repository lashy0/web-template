import pytest
from pydantic import ValidationError

from app.modules.batch.schemas import (
    CreateBatchReceiptRequest,
    CreateBatchRequest,
    UpdateBatchRequest,
    VoidBatchReceiptRequest,
    VoidBatchShipmentRequest,
)


@pytest.mark.unit
def test_batch_name_is_trimmed() -> None:
    payload = CreateBatchRequest.model_validate(
        {
            "name": "  August production  ",
            "dev_eui_prefix": "a1b2c3d4e5",
            "planned_qty": 100,
            "day_plan_qty": 20,
        }
    )

    assert payload.name == "August production"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        pytest.param(
            CreateBatchRequest,
            {"name": "Batch", "dev_eui_prefix": "a1b2c3d4e5", "planned_qty": 0, "day_plan_qty": 10},
            id="non-positive-planned-quantity",
        ),
        pytest.param(
            CreateBatchRequest,
            {"name": "Batch", "dev_eui_prefix": "a1b2c3d4e5", "planned_qty": 10, "day_plan_qty": 0},
            id="non-positive-day-plan-quantity",
        ),
        pytest.param(UpdateBatchRequest, {"day_plan_qty": 0}, id="non-positive-updated-day-plan"),
        pytest.param(CreateBatchReceiptRequest, {"quantity": 0}, id="non-positive-receipt"),
    ],
)
def test_batch_quantity_fields_must_be_positive(
    schema: type[CreateBatchRequest | UpdateBatchRequest | CreateBatchReceiptRequest],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


@pytest.mark.unit
@pytest.mark.parametrize(
    "schema",
    [
        pytest.param(VoidBatchReceiptRequest, id="receipt"),
        pytest.param(VoidBatchShipmentRequest, id="shipment"),
    ],
)
def test_void_reason_is_trimmed_and_cannot_be_empty(
    schema: type[VoidBatchReceiptRequest | VoidBatchShipmentRequest],
) -> None:
    assert schema.model_validate({"reason": "  duplicate  "}).reason == "duplicate"

    with pytest.raises(ValidationError):
        schema.model_validate({"reason": ""})
