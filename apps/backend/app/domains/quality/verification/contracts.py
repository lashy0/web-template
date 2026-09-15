from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VerificationKg:
    dev_eui: str
    state: str


class VerificationKgPort(Protocol):
    """Consumer-owned KG facts; locking is performed by the production adapter."""

    async def resolve_and_lock(
        self, *, dev_eui: str, related_dev_euis: list[str]
    ) -> VerificationKg | None: ...


class VerificationPakPort(Protocol):
    """Minimal identity observed from a legacy PAK machine principal."""

    @property
    def id(self) -> UUID: ...

    @property
    def code(self) -> str: ...

    @property
    def oauth_client_id(self) -> str: ...
