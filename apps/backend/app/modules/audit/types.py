from dataclasses import dataclass
from typing import Self
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuditActor:
    type: str
    id: str | None = None
    display_name: str | None = None
    identifier: str | None = None

    @classmethod
    def user(
        cls,
        user_id: UUID | str,
        *,
        name: str | None = None,
        login: str | None = None
    ) -> Self:
        return cls(
            type="user",
            id=str(user_id),
            display_name=name,
            identifier=login,
        )

    @classmethod
    def system(cls) -> Self:
        return cls(
            type="system",
            id=None,
        )


@dataclass(frozen=True, slots=True)
class AuditEntity:
    type: str
    id: str | None = None
    display_name: str | None = None
    identifier: str | None = None

    @classmethod
    def user(
        cls,
        user_id: UUID | str,
        *,
        name: str | None = None,
        login: str | None = None,
    ) -> Self:
        return cls(
            type="user",
            id=str(user_id),
            display_name=name,
            identifier=login,
        )
