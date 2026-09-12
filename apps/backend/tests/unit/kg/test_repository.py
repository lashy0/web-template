from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.kg.repositories import KgRepository
from app.modules.kg.schemas.state import KgCurrentState


@pytest.mark.unit
async def test_list_batch_items_returns_latest_session_data_in_one_query() -> None:
    batch_id = uuid4()
    result = SimpleNamespace(
        tuples=lambda: [
            (
                "a1b2c3d4e5f60708",
                KgCurrentState.OTK_PASSED,
                "1.4.2",
                None,
                2,
            ),
            (
                "a1b2c3d4e5f60709",
                KgCurrentState.REGISTERED,
                None,
                None,
                2,
            ),
        ]
    )
    session = SimpleNamespace(execute=AsyncMock(return_value=result))

    items, total = await KgRepository(session).list_batch_items(
        batch_id,
        page=1,
        page_size=25,
        q=None,
        current_state=None,
    )

    assert [item.dev_eui for item in items] == ["a1b2c3d4e5f60708", "a1b2c3d4e5f60709"]
    assert items[0].firmware_version == "1.4.2"
    assert items[0].current_state is KgCurrentState.OTK_PASSED
    assert items[1].current_state is KgCurrentState.REGISTERED
    assert items[1].firmware_version is None
    assert items[1].last_verification_at is None
    assert total == 2
    session.execute.assert_awaited_once()
