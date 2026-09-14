from datetime import datetime, timedelta

from app.modules.batch.exceptions import (
    BatchReceiptAlreadyVoidedError,
    BatchReceiptEditNotAllowedError,
    BatchReceiptEditWindowExpiredError,
)
from app.shared.security import CurrentPrincipal, Role

from .model import BatchReceipt


def ensure_active(receipt: BatchReceipt) -> None:
    if receipt.voided_at is not None:
        raise BatchReceiptAlreadyVoidedError


def ensure_edit_allowed(
    receipt: BatchReceipt,
    *,
    actor: CurrentPrincipal,
    now: datetime,
    edit_window: timedelta,
) -> None:
    if actor.role is Role.ADMINISTRATOR:
        return
    if receipt.created_by_user_id != actor.user_id:
        raise BatchReceiptEditNotAllowedError
    if now - receipt.created_at > edit_window:
        raise BatchReceiptEditWindowExpiredError
