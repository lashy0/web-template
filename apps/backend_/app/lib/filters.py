"""Collection filters shared by list endpoints, next to Advanced Alchemy's own."""

from typing import Annotated

from advanced_alchemy.filters import FilterTypes, NotNullFilter, NullFilter
from litestar.params import QueryParameter


def provide_archived_filter(
    archived: Annotated[
        bool | None,
        QueryParameter(description="Only archived (true) or only current (false) items; all when omitted."),
    ] = None,
) -> list[FilterTypes]:
    """Filter a list by its model's ``archived_at``.

    Register it as ``archived_filter`` next to the Advanced Alchemy ``filters``
    and pass both to ``get_many_and_count``.
    """
    if archived is None:
        return []

    return [NotNullFilter("archived_at") if archived else NullFilter("archived_at")]


__all__ = ("provide_archived_filter",)
