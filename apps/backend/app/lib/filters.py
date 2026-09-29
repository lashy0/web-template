"""Collection filters shared by list endpoints, next to Advanced Alchemy's own."""

from collections.abc import Callable
from typing import Annotated

from advanced_alchemy.filters import CollectionFilter, FilterTypes, NotNullFilter, NullFilter
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


def create_active_filter_provider(field_name: str) -> Callable[..., list[FilterTypes]]:
    """Return a provider that filters a list by the boolean column ``field_name``.

    Register it as ``active_filter`` like ``provide_archived_filter``; the query
    parameter is ``active`` whatever the column is called.
    """

    def provide_active_filter(
        active: Annotated[
            bool | None,
            QueryParameter(description="Only active (true) or only inactive (false) items; all when omitted."),
        ] = None,
    ) -> list[FilterTypes]:
        if active is None:
            return []

        return [CollectionFilter(field_name, [active])]

    return provide_active_filter


__all__ = ("create_active_filter_provider", "provide_archived_filter")
