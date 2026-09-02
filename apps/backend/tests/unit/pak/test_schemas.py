from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.pak.schemas.common import PakTestListResponse, PakTestResponse


@pytest.mark.unit
def test_pak_test_response_serializes_catalog_fields() -> None:
    test_id = uuid4()
    group_id = uuid4()
    observed_at = datetime(2026, 9, 2, 8, 30, tzinfo=UTC)

    response = PakTestResponse.model_validate(
        {
            "id": str(test_id),
            "test_name": "INSULATION_RESISTANCE",
            "test_label": "Insulation resistance",
            "defect_group_id": str(group_id),
            "last_seen_at": observed_at,
            "created_at": observed_at,
            "updated_at": observed_at,
        }
    )

    assert response.model_dump(mode="json") == {
        "id": str(test_id),
        "test_name": "INSULATION_RESISTANCE",
        "test_label": "Insulation resistance",
        "defect_group_id": str(group_id),
        "last_seen_at": "2026-09-02T08:30:00Z",
        "created_at": "2026-09-02T08:30:00Z",
        "updated_at": "2026-09-02T08:30:00Z",
    }


@pytest.mark.unit
def test_pak_test_list_response_requires_pagination_and_complete_items() -> None:
    with pytest.raises(ValidationError):
        PakTestListResponse.model_validate(
            {
                "items": [{"test_name": "INSULATION_RESISTANCE"}],
                "total": 1,
                "page": 1,
            }
        )
