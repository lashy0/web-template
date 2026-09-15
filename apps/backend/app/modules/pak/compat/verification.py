"""Translate the legacy PAK principal into quality's minimal consumer contract."""

from typing import Protocol
from uuid import UUID

from app.contexts.quality.verification.contracts import VerificationPakPort


class LegacyPakIdentity(Protocol):
    @property
    def id(self) -> UUID: ...

    @property
    def code(self) -> str: ...

    @property
    def oauth_client_id(self) -> str: ...


class LegacyVerificationPakAdapter:
    def __init__(self, pak: LegacyPakIdentity) -> None:
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


def adapt_pak(pak: LegacyPakIdentity) -> VerificationPakPort:
    return LegacyVerificationPakAdapter(pak)
