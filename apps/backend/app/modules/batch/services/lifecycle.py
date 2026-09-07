from __future__ import annotations

from datetime import datetime, timedelta

from app.auth.exceptions import ForbiddenError
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role

from ..exceptions import (
    BatchAlreadyCompletedError,
    BatchArchivedError,
    BatchEditNotAllowedError,
    BatchEditWindowExpiredError,
    BatchReceiptAlreadyVoidedError,
    BatchReceiptEditNotAllowedError,
    BatchReceiptEditWindowExpiredError,
    BatchShipmentAlreadyCompletedError,
    BatchShipmentAlreadyVoidedError,
    BatchShipmentEditNotAllowedError,
    BatchShipmentEditWindowExpiredError,
)
from ..models import Batch, BatchReceipt, BatchShipment, BatchStatus

BATCH_EDIT_WINDOW = timedelta(minutes=60)


def ensure_management_allowed(actor: CurrentPrincipal) -> None:
    if actor.role not in (Role.ADMINISTRATOR, Role.MANAGER):
        raise ForbiddenError


def ensure_not_archived(batch: Batch) -> None:
    if batch.archived_at is not None:
        raise BatchArchivedError


def ensure_in_production(batch: Batch) -> None:
    ensure_not_archived(batch)

    if batch.status == BatchStatus.COMPLETED:
        raise BatchAlreadyCompletedError


def ensure_batch_edit_allowed(
    batch: Batch,
    *,
    actor: CurrentPrincipal,
    now: datetime,
    edit_window: timedelta = BATCH_EDIT_WINDOW,
) -> None:
    if actor.role == Role.ADMINISTRATOR:
        return

    if batch.created_by_user_id != actor.user_id:
        raise BatchEditNotAllowedError

    if now - batch.created_at > edit_window:
        raise BatchEditWindowExpiredError


def ensure_receipt_active(receipt: BatchReceipt) -> None:
    if receipt.voided_at is not None:
        raise BatchReceiptAlreadyVoidedError


def ensure_receipt_edit_allowed(
    receipt: BatchReceipt,
    *,
    actor: CurrentPrincipal,
    now: datetime,
    edit_window: timedelta = BATCH_EDIT_WINDOW,
) -> None:
    if actor.role == Role.ADMINISTRATOR:
        return

    if receipt.created_by_user_id != actor.user_id:
        raise BatchReceiptEditNotAllowedError

    if now - receipt.created_at > edit_window:
        raise BatchReceiptEditWindowExpiredError


def ensure_shipment_not_voided(shipment: BatchShipment) -> None:
    if shipment.voided_at is not None:
        raise BatchShipmentAlreadyVoidedError


def ensure_shipment_open(shipment: BatchShipment) -> None:
    ensure_shipment_not_voided(shipment)

    if shipment.completed_at is not None:
        raise BatchShipmentAlreadyCompletedError


def ensure_shipment_edit_allowed(
    shipment: BatchShipment,
    *,
    actor: CurrentPrincipal,
    now: datetime,
    edit_window: timedelta = BATCH_EDIT_WINDOW,
) -> None:
    if actor.role == Role.ADMINISTRATOR:
        return

    if shipment.created_by_user_id != actor.user_id:
        raise BatchShipmentEditNotAllowedError

    if shipment.completed_at is None:
        return

    if now - shipment.completed_at > edit_window:
        raise BatchShipmentEditWindowExpiredError
