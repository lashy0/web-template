from collections.abc import Mapping
from uuid import UUID

from app.modules.audit.types import AuditActor, AuditEntity
from app.modules.kg.exceptions import KgDevEuiPrefixNotFoundError, KgVersionNotFoundError
from app.modules.kg.permissions import KgPermission
from app.shared.security import CurrentPrincipal, ForbiddenError

from ..model import KgDevEuiPrefix, KgVersion
from ..repository import KgRepository


def authorize(actor: CurrentPrincipal, permission: KgPermission) -> None:
    if not actor.has_permission(permission):
        raise ForbiddenError


async def required_prefix(repository: KgRepository, prefix: str) -> KgDevEuiPrefix:
    item = await repository.get_prefix(prefix, for_update=True)
    if item is None:
        raise KgDevEuiPrefixNotFoundError
    return item


async def required_version(repository: KgRepository, version_id: UUID) -> KgVersion:
    item = await repository.get_version(version_id, for_update=True)
    if item is None:
        raise KgVersionNotFoundError
    return item


def audit_actor(actor: CurrentPrincipal) -> AuditActor:
    return AuditActor.user(actor.user_id, name=actor.name, login=actor.login)


def prefix_entity(item: KgDevEuiPrefix) -> AuditEntity:
    return AuditEntity(
        type="kg_dev_eui_prefix",
        id=item.prefix,
        display_name=item.name or item.prefix,
        identifier=item.prefix,
    )


def version_entity(item: KgVersion) -> AuditEntity:
    return AuditEntity(
        type="kg_version", id=str(item.id), display_name=item.name, identifier=item.code
    )


def changed_values(
    item: object, updates: Mapping[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    old = {field: getattr(item, field) for field in updates}
    return old, {field: getattr(item, field) for field in updates}
