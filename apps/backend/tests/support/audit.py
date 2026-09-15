"""An audit collaborator that records instead of asserting on call shape."""

from dataclasses import dataclass, field
from typing import Any

from app.audit.types import AuditActor, AuditEntity
from app.audit.writer import ACTION_PATTERN


@dataclass(frozen=True, slots=True)
class AuditRecord:
    actor: AuditActor
    action: str
    entity: AuditEntity
    old_data: dict[str, Any] | None = None
    new_data: dict[str, Any] | None = None


@dataclass(slots=True)
class RecordingAudit:
    """Collects audit records so tests can assert on what was audited.

    The action format is validated with the production pattern, so a command
    that emits a malformed action fails here exactly as it would in production.
    """

    records: list[AuditRecord] = field(default_factory=list)

    async def record(
        self,
        *,
        actor: AuditActor,
        entity: AuditEntity,
        action: str,
        old_data: dict[str, Any] | None = None,
        new_data: dict[str, Any] | None = None,
    ) -> AuditRecord:
        if not ACTION_PATTERN.fullmatch(action):
            raise ValueError("Audit action must use '<namespace>.<operation>' format")

        entry = AuditRecord(
            actor=actor,
            action=action,
            entity=entity,
            old_data=old_data,
            new_data=new_data,
        )
        self.records.append(entry)
        return entry

    @property
    def actions(self) -> list[str]:
        return [entry.action for entry in self.records]

    @property
    def nothing_was_audited(self) -> bool:
        return not self.records

    @property
    def only(self) -> AuditRecord:
        """The single audit record, failing loudly when that is not the case."""
        if len(self.records) != 1:
            raise AssertionError(f"expected exactly one audit record, got {self.actions}")
        return self.records[0]
