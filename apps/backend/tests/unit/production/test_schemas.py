import msgspec
import pytest

from app.domain.production.schemas import (
    BatchReceiptUpdate,
    BatchReceiptVoid,
    BatchShipmentComplete,
    BatchShipmentUnitsAdd,
    BatchShipmentUpdate,
    BatchUpdate,
    KgPrefixCreate,
    KgPrefixUpdate,
    KgVersionCreate,
    KgVersionUpdate,
    ProductionOrderCreate,
    ProductionOrderUpdate,
)
from app.lib.concurrency import update_changes
from app.lib.lorawan import InvalidDevEuiPrefixError
from app.lib.validation import ValidationError

READ_AT = "2026-10-05T12:00:00+00:00"
"""The `updatedAt` of the copy an update is made from."""

pytestmark = pytest.mark.unit


def test_production_order_create_strips_name() -> None:
    data = ProductionOrderCreate(name="  Order 1  ")

    assert data.name == "Order 1"


def test_production_order_create_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        ProductionOrderCreate(name="   ")


def test_production_order_create_rejects_too_long_description() -> None:
    with pytest.raises(ValidationError):
        ProductionOrderCreate(name="Order", description="x" * 2001)


def test_production_order_update_requires_a_field() -> None:
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"expectedUpdatedAt": READ_AT}, ProductionOrderUpdate)


def test_production_order_update_accepts_cleared_description() -> None:
    data = msgspec.convert({"expectedUpdatedAt": READ_AT, "description": None}, ProductionOrderUpdate)

    assert update_changes(data) == {"description": None}


def test_kg_prefix_create_normalizes_prefix_and_short_code() -> None:
    data = KgPrefixCreate(prefix=" A1B2C3D4E5 ", short_code=" AB1 ")

    assert (data.prefix, data.short_code) == ("a1b2c3d4e5", "ab1")


def test_kg_prefix_create_rejects_malformed_prefix() -> None:
    with pytest.raises(InvalidDevEuiPrefixError):
        KgPrefixCreate(prefix="a1b2c3d4", short_code="ab1")


def test_kg_prefix_create_rejects_short_code_with_separator() -> None:
    with pytest.raises(ValidationError):
        KgPrefixCreate(prefix="a1b2c3d4e5", short_code="ab-1")


def test_kg_prefix_update_requires_a_field() -> None:
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"expectedUpdatedAt": READ_AT}, KgPrefixUpdate)


def test_kg_version_create_rejects_too_long_code() -> None:
    with pytest.raises(ValidationError):
        KgVersionCreate(code="v" * 33, name="Version")


def test_kg_prefix_create_rejects_too_long_short_code() -> None:
    with pytest.raises(ValidationError):
        KgPrefixCreate(prefix="a1b2c3d4e5", short_code="a" * 11)


def test_kg_prefix_update_accepts_cleared_name() -> None:
    data = msgspec.convert({"expectedUpdatedAt": READ_AT, "name": None}, KgPrefixUpdate)

    assert update_changes(data) == {"name": None}


def test_kg_version_update_requires_a_field() -> None:
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"expectedUpdatedAt": READ_AT}, KgVersionUpdate)


def test_kg_version_update_accepts_cleared_description() -> None:
    data = msgspec.convert({"expectedUpdatedAt": READ_AT, "description": None}, KgVersionUpdate)

    assert update_changes(data) == {"description": None}


def test_batch_update_requires_a_field() -> None:
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"expectedUpdatedAt": READ_AT}, BatchUpdate)


def test_batch_receipt_update_requires_a_field() -> None:
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"expectedUpdatedAt": READ_AT}, BatchReceiptUpdate)


def test_batch_receipt_void_requires_a_reason() -> None:
    with pytest.raises(ValidationError):
        BatchReceiptVoid(reason="   ")


def test_batch_shipment_update_requires_the_comment() -> None:
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"expectedUpdatedAt": READ_AT}, BatchShipmentUpdate)


def test_batch_shipment_complete_requires_a_positive_quantity() -> None:
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"expectedQuantity": 0}, BatchShipmentComplete)


def test_batch_shipment_units_add_rejects_more_codes_than_one_request_takes() -> None:
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"codes": ["ab1-000001"] * 1001}, BatchShipmentUnitsAdd)
