from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.auth.permissions import permissions_for_role
from app.auth.roles import Role
from app.modules.batch.permissions import BatchPermission
from app.modules.production_order.permissions import ProductionOrderPermission
from app.modules.production_order.schemas import (
    AssignProductionOrderRequest,
    CreateProductionOrderRequest,
    UpdateProductionOrderRequest,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("name", ["", "   ", None, "a" * 129])
@pytest.mark.parametrize("schema", [CreateProductionOrderRequest, UpdateProductionOrderRequest])
def test_invalid_names_are_rejected(schema, name):
    with pytest.raises(ValidationError):
        schema(name=name)


def test_update_distinguishes_omitted_fields_and_cleared_description():
    assert UpdateProductionOrderRequest().model_dump(exclude_unset=True) == {}
    assert UpdateProductionOrderRequest(description=None).model_dump(exclude_unset=True) == {
        "description": None
    }
    assert CreateProductionOrderRequest(name="  Order  ").name == "Order"


@pytest.mark.parametrize("field", ["updated_at", "archived_at", "id", "batches_count"])
@pytest.mark.parametrize("schema", [CreateProductionOrderRequest, UpdateProductionOrderRequest])
def test_server_owned_fields_cannot_be_written(schema, field):
    payload = schema(name="Order", **{field: None})
    assert payload.model_dump(exclude_unset=True) == {"name": "Order"}


def test_assignment_requires_explicit_id_or_null():
    with pytest.raises(ValidationError):
        AssignProductionOrderRequest()
    assert AssignProductionOrderRequest(production_order_id=None).production_order_id is None
    order_id = uuid4()
    assert (
        AssignProductionOrderRequest(production_order_id=order_id).production_order_id == order_id
    )


@pytest.mark.parametrize("role", list(Role))
def test_order_management_permissions(role):
    expected = role in (Role.MANAGER, Role.ADMINISTRATOR)
    permissions = permissions_for_role(role)
    assert (BatchPermission.ASSIGN_PRODUCTION_ORDER in permissions) == expected
    for permission in ProductionOrderPermission:
        assert (permission in permissions) == expected
