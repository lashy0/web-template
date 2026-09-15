from datetime import datetime, timedelta

from app.domains.production.exceptions import (
    BatchShipmentAlreadyCompletedError,
    BatchShipmentAlreadyVoidedError,
    BatchShipmentEditNotAllowedError,
    BatchShipmentEditWindowExpiredError,
)
from app.shared.security import CurrentPrincipal, Role

from .model import BatchShipment


def ensure_not_voided(shipment: BatchShipment) -> None:
    if shipment.voided_at is not None:
        raise BatchShipmentAlreadyVoidedError


def ensure_open(shipment: BatchShipment) -> None:
    ensure_not_voided(shipment)
    if shipment.completed_at is not None:
        raise BatchShipmentAlreadyCompletedError


def ensure_edit_allowed(
    shipment: BatchShipment,
    *,
    actor: CurrentPrincipal,
    now: datetime,
    edit_window: timedelta,
) -> None:
    if actor.role is Role.ADMINISTRATOR:
        return
    if shipment.created_by_user_id != actor.user_id:
        raise BatchShipmentEditNotAllowedError
    if shipment.completed_at is not None and now - shipment.completed_at > edit_window:
        raise BatchShipmentEditWindowExpiredError
