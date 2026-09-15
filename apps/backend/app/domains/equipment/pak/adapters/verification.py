from uuid import UUID

from app.domains.quality.verification.contracts import VerificationPakPort

from ..model import PakDevice


class EquipmentVerificationPakAdapter:
    """Expose only verification's PAK identity facts."""

    def __init__(self, pak: PakDevice) -> None:
        self._pak = pak

    @property
    def id(self) -> UUID:
        return self._pak.id

    @property
    def code(self) -> str:
        return self._pak.code

    @property
    def oauth_client_id(self) -> str:
        return self._pak.oauth_client_id


def adapt_pak(pak: PakDevice) -> VerificationPakPort:
    return EquipmentVerificationPakAdapter(pak)
