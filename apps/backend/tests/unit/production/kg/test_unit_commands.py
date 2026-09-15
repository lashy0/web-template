from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.auth.roles import Role
from app.contexts.production.kg.commands import DeleteKg, SetKgState
from app.contexts.production.kg.exceptions import KgCannotBeDeletedError
from app.contexts.production.kg.model import KgState
from app.shared.security import CurrentPrincipal


def _actor() -> CurrentPrincipal:
    return CurrentPrincipal(
        user_id=uuid4(), identity_id=uuid4(), session_id=uuid4(), role=Role.ADMINISTRATOR
    )


def _kg(state: KgState = KgState.REGISTERED) -> SimpleNamespace:
    return SimpleNamespace(dev_eui="a1b2c3d4e5000001", batch_id=uuid4(), state=state)


@pytest.mark.unit
async def test_set_state_updates_persistent_state_and_writes_transactional_audit() -> None:
    kg = _kg()
    repository = SimpleNamespace(
        get_by_dev_eui=AsyncMock(return_value=kg),
        update_state=AsyncMock(
            side_effect=lambda item, **values: setattr(item, "state", values["state"]) or item
        ),
    )
    audit = SimpleNamespace(record=AsyncMock())

    updated = await SetKgState(repository, audit).execute(
        actor=_actor(), dev_eui=kg.dev_eui, state=KgState.SCRAPPED
    )

    assert updated.state is KgState.SCRAPPED
    assert audit.record.await_args.kwargs["action"] == "kg.state_changed"


@pytest.mark.unit
async def test_delete_rejects_verification_history_without_touching_row() -> None:
    kg = _kg()
    repository = SimpleNamespace(get_by_dev_eui=AsyncMock(return_value=kg), delete_unit=AsyncMock())
    history = SimpleNamespace(has_history_for_kg=AsyncMock(return_value=True))

    with pytest.raises(KgCannotBeDeletedError):
        await DeleteKg(repository, history, SimpleNamespace(record=AsyncMock())).execute(
            actor=_actor(), dev_eui=kg.dev_eui
        )

    repository.delete_unit.assert_not_awaited()


@pytest.mark.unit
async def test_delete_registered_kg_without_history_audits_then_removes_row() -> None:
    kg = _kg()
    repository = SimpleNamespace(get_by_dev_eui=AsyncMock(return_value=kg), delete_unit=AsyncMock())
    history = SimpleNamespace(has_history_for_kg=AsyncMock(return_value=False))
    audit = SimpleNamespace(record=AsyncMock())

    await DeleteKg(repository, history, audit).execute(actor=_actor(), dev_eui=kg.dev_eui)

    repository.delete_unit.assert_awaited_once_with(kg)
    assert audit.record.await_args.kwargs["action"] == "kg.deleted"
