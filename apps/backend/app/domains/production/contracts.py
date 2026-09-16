"""Outbound ports owned by the production module.

Production is one consistency boundary: batches, receipts, shipments,
preparation, KG and production orders change inside a single transaction and
import each other directly.  This module declares only what production needs
from *another* module, so a reader can see the module's whole external surface
in one place.
"""

from typing import Protocol
from uuid import UUID

from sqlalchemy.sql.selectable import Subquery


class VerificationHistoryPort(Protocol):
    """Verification facts that production deletion rules depend on.

    Implemented by quality; production never reads verification tables itself.
    """

    async def has_history_for_batch(self, batch_id: UUID) -> bool: ...

    async def has_history_for_kg(self, dev_eui: str) -> bool: ...


class LatestVerificationProjectionPort(Protocol):
    """Latest verification relation required by production KG read models.

    The relation is supplied by infrastructure. Production owns the shape it
    consumes but does not import quality's ORM mapping or query.
    """

    def latest_verification_projection(self) -> Subquery: ...
