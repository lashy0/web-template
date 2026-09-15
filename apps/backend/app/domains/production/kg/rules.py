"""Evidenced KG prefix/version policies; arithmetic stays in components.keygen."""

from .exceptions import KgDevEuiPrefixArchivedError
from .model import KgDevEuiPrefix


def ensure_prefix_available_for_allocation(prefix: KgDevEuiPrefix) -> None:
    if prefix.archived_at is not None:
        raise KgDevEuiPrefixArchivedError
