from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.contracts import TokenIntrospector
from app.auth.exceptions import ForbiddenError

from ..exceptions import InvalidMachineAccessTokenError
from ..models import PakDevice
from ..repository import PakRepository

PAK_LAST_SEEN_UPDATE_INTERVAL = timedelta(seconds=15)


class PakAuthenticationService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        token_introspector: TokenIntrospector,
    ) -> None:
        self._session_factory = session_factory
        self._token_introspector = token_introspector

    async def authorize_machine_access_token(self, access_token: str) -> PakDevice:
        """Authorize a PAK token against live local active/archive state."""
        introspection = await self._token_introspector.introspect_access_token(access_token)

        if not introspection.active or not introspection.client_id:
            raise InvalidMachineAccessTokenError

        async with self._session_factory() as session, session.begin():
            repository = PakRepository(session)

            pak = await repository.get_by_oauth_client_id(introspection.client_id)

            if pak is None:
                raise InvalidMachineAccessTokenError

            if not pak.is_active or pak.archived_at is not None:
                raise ForbiddenError("PAK is inactive or archived")

            now = datetime.now(UTC)

            if pak.last_seen_at is None or now - pak.last_seen_at >= PAK_LAST_SEEN_UPDATE_INTERVAL:
                pak = await repository.update_last_seen(pak, last_seen_at=now)

            return pak
