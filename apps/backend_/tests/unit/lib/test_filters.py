import pytest
from advanced_alchemy.filters import NotNullFilter, NullFilter

from app.lib.filters import provide_archived_filter

pytestmark = pytest.mark.unit


def test_provide_archived_filter_selects_archived_items() -> None:
    assert provide_archived_filter(archived=True) == [NotNullFilter("archived_at")]


def test_provide_archived_filter_selects_current_items() -> None:
    assert provide_archived_filter(archived=False) == [NullFilter("archived_at")]


def test_provide_archived_filter_keeps_all_items_when_omitted() -> None:
    assert provide_archived_filter() == []
