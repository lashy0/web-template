from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domains.production.exceptions import (
    BatchReceiptAlreadyVoidedError,
    BatchReceiptEditNotAllowedError,
    BatchShipmentAlreadyCompletedError,
    BatchShipmentAlreadyVoidedError,
    BatchShipmentEditNotAllowedError,
)
from app.domains.production.receipts.model import BatchReceipt
from app.domains.production.receipts.rules import ensure_active
from app.domains.production.receipts.rules import ensure_edit_allowed as receipt_edit_allowed
from app.domains.production.shipments.model import BatchShipment
from app.domains.production.shipments.rules import ensure_edit_allowed as shipment_edit_allowed
from app.domains.production.shipments.rules import ensure_not_voided, ensure_open
from app.shared.security import CurrentPrincipal, Role


def principal(user_id, role: Role = Role.MANAGER) -> CurrentPrincipal:
    return CurrentPrincipal(
        user_id=user_id,
        identity_id=uuid4(),
        session_id=uuid4(),
        role=role,
        name="operator",
        login="operator",
    )


def receipt(*, owner_id, voided: bool = False) -> BatchReceipt:
    now = datetime.now(UTC)
    return BatchReceipt(
        batch_id=uuid4(),
        quantity=1,
        created_by_user_id=owner_id,
        created_at=now,
        updated_at=now,
        voided_at=now if voided else None,
    )


def shipment(*, owner_id, completed: bool = False, voided: bool = False) -> BatchShipment:
    now = datetime.now(UTC)
    return BatchShipment(
        batch_id=uuid4(),
        created_by_user_id=owner_id,
        created_at=now,
        updated_at=now,
        completed_at=now if completed else None,
        voided_at=now if voided else None,
    )


@pytest.mark.unit
def test_receipt_owner_window_and_admin_bypass() -> None:
    owner = uuid4()
    document = receipt(owner_id=owner)
    receipt_edit_allowed(
        document, actor=principal(owner), now=datetime.now(UTC), edit_window=timedelta(hours=1)
    )
    receipt_edit_allowed(
        document,
        actor=principal(uuid4(), Role.ADMINISTRATOR),
        now=datetime.now(UTC),
        edit_window=timedelta(0),
    )
    with pytest.raises(BatchReceiptEditNotAllowedError):
        receipt_edit_allowed(
            document,
            actor=principal(uuid4()),
            now=datetime.now(UTC),
            edit_window=timedelta(hours=1),
        )


@pytest.mark.unit
def test_voided_receipt_is_not_mutable() -> None:
    with pytest.raises(BatchReceiptAlreadyVoidedError):
        ensure_active(receipt(owner_id=uuid4(), voided=True))


@pytest.mark.unit
def test_shipment_open_and_owner_rules() -> None:
    owner = uuid4()
    with pytest.raises(BatchShipmentAlreadyCompletedError):
        ensure_open(shipment(owner_id=owner, completed=True))
    with pytest.raises(BatchShipmentAlreadyVoidedError):
        ensure_not_voided(shipment(owner_id=owner, voided=True))
    with pytest.raises(BatchShipmentEditNotAllowedError):
        shipment_edit_allowed(
            shipment(owner_id=owner),
            actor=principal(uuid4()),
            now=datetime.now(UTC),
            edit_window=timedelta(hours=1),
        )
