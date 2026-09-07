from uuid import UUID

from ..exceptions import PakNotFoundError
from ..models import PakDevice
from ..repository import PakRepository


async def _required_pak(repository: PakRepository, pak_id: UUID) -> PakDevice:
    pak = await repository.get_by_id(pak_id, for_update=True)

    if pak is None:
        raise PakNotFoundError

    return pak
