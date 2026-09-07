from __future__ import annotations

from uuid import UUID

from ..exceptions import VerificationSessionNotFoundError
from ..models import VerificationSession
from ..repositories import VerificationSessionRepository


async def required_session_for_update(
    repository: VerificationSessionRepository,
    session_id: UUID,
) -> VerificationSession:
    verification_session = await repository.get_by_id_for_update(session_id)

    if verification_session is None:
        raise VerificationSessionNotFoundError

    return verification_session
