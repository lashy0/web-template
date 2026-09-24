import msgspec
import pytest

from app.domain.production.schemas import ProductionOrderCreate, ProductionOrderUpdate
from app.lib.validation import ValidationError

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
        msgspec.convert({}, ProductionOrderUpdate)


def test_production_order_update_accepts_cleared_description() -> None:
    data = msgspec.convert({"description": None}, ProductionOrderUpdate)

    assert data.to_dict() == {"description": None}
