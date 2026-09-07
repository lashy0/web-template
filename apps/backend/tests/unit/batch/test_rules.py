from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.auth.exceptions import ForbiddenError
from app.auth.roles import Role
from app.modules.batch import exceptions as errors
from app.modules.batch.models import BatchShipmentItem, BatchStatus
from app.modules.kg.models import KgStatus
from tests.unit.batch.test_service import (
    _batch,
    _kg,
    _principal,
    _receipt,
    _service,
    _shipment,
)
from tests.unit.batch.test_service import (
    dependencies as dependencies,
)

pytestmark = pytest.mark.unit


def setup(dependencies, *, status=BatchStatus.IN_PRODUCTION):
    batches, receipts, shipments, kg_units, _, _ = dependencies
    actor = _principal(role=Role.MANAGER)
    batch = _batch(created_by_user_id=actor.user_id, status=status)
    receipt = _receipt(batch_id=batch.id, created_by_user_id=actor.user_id)
    shipment = _shipment(batch_id=batch.id, created_by_user_id=actor.user_id)
    batches.return_value.get_by_id.return_value = batch
    receipts.return_value.get_by_id.return_value = receipt
    shipments.return_value.get_by_id.return_value = shipment
    shipments.return_value.find_non_voided_by_kg.return_value = None
    kg = _kg(batch_id=batch.id)
    kg_units.return_value.get_by_dev_eui.return_value = kg
    kg_units.return_value.get_many_by_dev_euis.return_value = [kg]
    shipments.return_value.list_items.return_value = [
        BatchShipmentItem(shipment_id=shipment.id, kg_dev_eui=kg.dev_eui)
    ]
    return actor, batch, receipt, shipment, kg


def arguments(method, actor, batch, receipt, shipment, kg):
    result = {"actor": actor, "batch_id": batch.id}
    if "receipt" in method and method != "create_receipt":
        result["receipt_id"] = receipt.id
    if "shipment" in method and method != "create_shipment":
        result["shipment_id"] = shipment.id
    if method in ("update", "update_receipt", "update_shipment"):
        result["updates"] = {}
    if method == "create_receipt":
        result.update(quantity=1, comment=None)
    if method == "create_shipment":
        result["comment"] = None
    if method.startswith("void"):
        result["reason"] = "return"
    if method in ("add_shipment_item", "remove_shipment_item"):
        result["dev_eui"] = kg.dev_eui
    return result


@pytest.mark.parametrize(
    "method",
    [
        "update",
        "complete",
        "delete",
        "create_receipt",
        "update_receipt",
        "void_receipt",
        "create_shipment",
        "update_shipment",
        "add_shipment_item",
        "remove_shipment_item",
        "complete_shipment",
        "void_shipment",
    ],
)
async def test_archived_batch_blocks_every_mutation(dependencies, method):
    actor, batch, receipt, shipment, kg = setup(dependencies)
    batch.archived_at = datetime.now(UTC)
    with pytest.raises(errors.BatchArchivedError):
        await getattr(_service(), method)(**arguments(method, actor, batch, receipt, shipment, kg))


@pytest.mark.parametrize(
    "method",
    ["complete", "create_receipt", "create_shipment", "add_shipment_item", "complete_shipment"],
)
async def test_completed_batch_rejects_new_production(dependencies, method):
    values = setup(dependencies, status=BatchStatus.COMPLETED)
    with pytest.raises(errors.BatchAlreadyCompletedError):
        await getattr(_service(), method)(**arguments(method, *values))


@pytest.mark.parametrize(
    "method", ["update", "update_receipt", "void_receipt", "update_shipment", "void_shipment"]
)
async def test_completed_batch_allows_existing_document_corrections(dependencies, method):
    values = setup(dependencies, status=BatchStatus.COMPLETED)
    await getattr(_service(), method)(**arguments(method, *values))


@pytest.mark.parametrize("invalid", ["missing", "wrong_batch", "not_packed", "assigned"])
async def test_invalid_kg_cannot_be_added(dependencies, invalid):
    values = setup(dependencies)
    _, _, shipments, kg_units, _, _ = dependencies
    kg = values[-1]
    error = {
        "missing": errors.BatchShipmentKgNotFoundError,
        "wrong_batch": errors.BatchShipmentKgWrongBatchError,
        "not_packed": errors.BatchShipmentKgNotPackedError,
        "assigned": errors.BatchShipmentKgAlreadyAssignedError,
    }[invalid]
    if invalid == "missing":
        kg_units.return_value.get_by_dev_eui.return_value = None
    elif invalid == "wrong_batch":
        kg.batch_id = uuid4()
    elif invalid == "not_packed":
        kg.status = KgStatus.TESTING
    else:
        shipments.return_value.find_non_voided_by_kg.return_value = object()
    with pytest.raises(error):
        await _service().add_shipment_item(**arguments("add_shipment_item", *values))
    shipments.return_value.add_item.assert_not_awaited()


@pytest.mark.parametrize(
    "method", ["update_shipment", "add_shipment_item", "remove_shipment_item", "complete_shipment"]
)
@pytest.mark.parametrize("state", ["completed", "voided"])
async def test_closed_shipment_rejects_edits_and_repeat_completion(dependencies, method, state):
    values = setup(dependencies)
    shipment = values[3]
    setattr(shipment, "completed_at" if state == "completed" else "voided_at", datetime.now(UTC))
    error = (
        errors.BatchShipmentAlreadyCompletedError
        if state == "completed"
        else errors.BatchShipmentAlreadyVoidedError
    )
    with pytest.raises(error):
        await getattr(_service(), method)(**arguments(method, *values))


@pytest.mark.parametrize("method", ["update_receipt", "void_receipt", "void_shipment"])
async def test_voided_documents_cannot_be_changed_or_voided_again(dependencies, method):
    values = setup(dependencies)
    values[2].voided_at = values[3].voided_at = datetime.now(UTC)
    error = (
        errors.BatchReceiptAlreadyVoidedError
        if "receipt" in method
        else errors.BatchShipmentAlreadyVoidedError
    )
    with pytest.raises(error):
        await getattr(_service(), method)(**arguments(method, *values))


async def test_void_does_not_overwrite_unexpected_kg_state(dependencies):
    values = setup(dependencies)
    values[3].completed_at = datetime.now(UTC)
    values[-1].status = KgStatus.SCRAPPED
    with pytest.raises(errors.BatchShipmentKgStateConflictError):
        await _service().void_shipment(**arguments("void_shipment", *values))
    dependencies[3].return_value.update_status_many.assert_not_awaited()
    dependencies[2].return_value.void.assert_not_awaited()


@pytest.mark.parametrize(
    "method,error",
    [
        ("update", errors.BatchEditWindowExpiredError),
        ("update_receipt", errors.BatchReceiptEditWindowExpiredError),
        ("void_shipment", errors.BatchShipmentEditWindowExpiredError),
    ],
)
async def test_manager_windows_and_administrator_override(dependencies, method, error):
    values = setup(dependencies)
    actor, batch, receipt, shipment, kg = values
    old = datetime.now(UTC) - timedelta(hours=2)
    batch.created_at = receipt.created_at = shipment.completed_at = old
    kg.status = KgStatus.SHIPPED
    with pytest.raises(error):
        await getattr(_service(), method)(**arguments(method, *values))
    await getattr(_service(), method)(
        **arguments(method, _principal(), batch, receipt, shipment, kg)
    )


async def test_service_blocks_non_management_roles(dependencies):
    _, batch, *_ = setup(dependencies)
    with pytest.raises(ForbiddenError):
        await _service().complete(actor=_principal(role=Role.ENGINEER), batch_id=batch.id)
    dependencies[0].return_value.get_by_id.assert_not_awaited()


@pytest.mark.parametrize(
    "method,error",
    [
        ("update_receipt", errors.BatchReceiptEditNotAllowedError),
        ("void_shipment", errors.BatchShipmentEditNotAllowedError),
    ],
)
async def test_manager_cannot_change_another_owners_document(dependencies, method, error):
    actor, batch, receipt, shipment, kg = setup(dependencies)
    other_manager = _principal(role=Role.MANAGER)
    with pytest.raises(error):
        await getattr(_service(), method)(
            **arguments(method, other_manager, batch, receipt, shipment, kg)
        )


async def test_integrity_failure_is_translated_to_domain_conflict(dependencies):
    values = setup(dependencies)
    dependencies[2].return_value.add_item.side_effect = IntegrityError(
        "private SQL", {}, Exception("private constraint details")
    )
    with pytest.raises(errors.BatchConflictError) as caught:
        await _service().add_shipment_item(**arguments("add_shipment_item", *values))
    assert "private" not in str(caught.value)
    dependencies[5].from_session.return_value.record.assert_not_awaited()
