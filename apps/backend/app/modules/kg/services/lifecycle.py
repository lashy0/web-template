from ..exceptions import KgCannotBeDeletedError, KgInvalidStateError
from ..models import KgState, KgUnit


def ensure_verification_ready(kg: KgUnit) -> None:
    if kg.state is not KgState.REGISTERED:
        raise KgInvalidStateError


def ensure_can_delete(kg: KgUnit) -> None:
    if kg.state is not KgState.REGISTERED:
        raise KgCannotBeDeletedError
