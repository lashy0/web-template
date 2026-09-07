from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.kg.exceptions import KgInvalidStateError
from app.modules.kg.models import KgStatus
from app.modules.kg.services import KgService
from tests.unit.kg.test_service import _kg, _Session
from tests.unit.kg.test_service import dependencies as dependencies

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "status", [s for s in KgStatus if s not in {KgStatus.REGISTERED, KgStatus.READY_FOR_RETEST}]
)
async def test_verification_cannot_start_from_invalid_state(dependencies, status):
    repository, _ = dependencies
    kg = _kg(status=status)
    repository.return_value.get_by_dev_eui.return_value = kg
    with pytest.raises(KgInvalidStateError):
        await KgService(cast(AsyncSession, _Session())).begin_verification(kg.dev_eui)
    repository.return_value.get_by_dev_eui.assert_awaited_once_with(kg.dev_eui, for_update=True)
    repository.return_value.update_status.assert_not_awaited()


@pytest.mark.parametrize("status", [s for s in KgStatus if s != KgStatus.TESTING])
async def test_verification_cannot_complete_from_invalid_state(dependencies, status):
    repository, _ = dependencies
    kg = _kg(status=status)
    repository.return_value.get_by_dev_eui.return_value = kg
    with pytest.raises(KgInvalidStateError):
        await KgService(cast(AsyncSession, _Session())).finish_verification(
            kg.dev_eui, status=KgStatus.READY_FOR_PACKING
        )
    repository.return_value.update_status.assert_not_awaited()
