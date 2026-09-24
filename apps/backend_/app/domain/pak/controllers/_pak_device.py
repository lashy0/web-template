"""PAK device controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import msgspec
from litestar import Controller, Request, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.db import models as m
from app.domain.admin.deps import provide_audit_log_service
from app.domain.admin.services import AuditLogService
from app.domain.pak.crypto import PakAccessKeyCipher
from app.domain.pak.deps import provide_pak_access_key_cipher
from app.domain.pak.permissions import PakPermission
from app.domain.pak.schemas import (
    PakAccessKey,
    PakDevice,
    PakDeviceCreate,
    PakDeviceProvisioned,
    PakDeviceUpdate,
)
from app.domain.pak.services import PakDeviceService
from app.lib.authorization import requires_permission
from app.lib.deps import create_service_dependencies
from app.lib.filters import provide_archived_filter
from app.lib.hydra import HydraClient
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

PakId = Annotated[UUID, Parameter(title="PAK ID", description="The PAK device to act on.")]


class PakDeviceController(Controller):
    """PAK devices."""

    tags = ["PAK devices"]  # noqa: RUF012
    path = "/paks"
    dependencies = create_service_dependencies(
        PakDeviceService,
        key="pak_devices_service",
        filters={
            "id_filter": UUID,
            "search": "code,oauth_client_id",
            "pagination_type": "limit_offset",
            "pagination_size": 20,
            "created_at": True,
            "updated_at": True,
            "sort_field": "code",
            "sort_order": "asc",
        },
    )
    dependencies["archived_filter"] = Provide(provide_archived_filter, sync_to_thread=False)
    dependencies["audit_service"] = Provide(provide_audit_log_service)
    dependencies["pak_cipher"] = Provide(provide_pak_access_key_cipher, sync_to_thread=False)

    @staticmethod
    async def _log_pak_action(
        request: Request[m.User, Any, Any],
        audit_service: AuditLogService,
        *,
        action: str,
        target: m.PakDevice,
        details: dict[str, Any] | None = None,
    ) -> None:
        await audit_service.log_action(
            action=action,
            actor_id=request.user.id,
            actor_login=request.user.identity_login,
            target_type="pak",
            target_id=str(target.id),
            target_label=target.code,
            details=details,
            request=request,
        )

    @get(
        operation_id="ListPakDevices",
        guards=[requires_permission(PakPermission.READ)],
        responses=error_responses(401, 403),
    )
    async def list_pak_devices(
        self,
        pak_devices_service: NamedDependency[PakDeviceService],
        filters: NamedDependency[SkipValidation[list[FilterTypes]]],
        archived_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[PakDevice]:
        results, total = await pak_devices_service.get_many_and_count(*filters, *archived_filter)

        return pak_devices_service.to_schema(
            results,
            total,
            filters,
            schema_type=PakDevice,
        )

    @get(
        operation_id="GetPakDevice",
        path="/{pak_id:uuid}",
        guards=[requires_permission(PakPermission.READ)],
        responses=error_responses(401, 403, 404),
    )
    async def get_pak_device(
        self,
        pak_devices_service: NamedDependency[PakDeviceService],
        pak_id: PakId,
    ) -> PakDevice:
        db_obj = await pak_devices_service.get(pak_id)

        return pak_devices_service.to_schema(
            db_obj,
            schema_type=PakDevice,
        )

    @post(
        operation_id="CreatePakDevice",
        path="",
        guards=[requires_permission(PakPermission.CREATE)],
        responses=error_responses(401, 403, 409, 503),
    )
    async def create_pak_device(
        self,
        request: Request[m.User, Any, Any],
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        pak_cipher: NamedDependency[PakAccessKeyCipher],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        data: PakDeviceCreate,
    ) -> PakDeviceProvisioned:
        db_obj, access_key = await pak_devices_service.create_pak(
            data.to_dict(),
            hydra=hydra,
            cipher=pak_cipher,
            uow=uow,
        )
        await self._log_pak_action(
            request,
            audit_service,
            action="pak.created",
            target=db_obj,
            details={
                "kind": data.kind.value,
                "is_active": data.is_active,
            },
        )

        return PakDeviceProvisioned(
            device=pak_devices_service.to_schema(
                db_obj,
                schema_type=PakDevice,
            ),
            access_key=access_key,
        )

    @patch(
        operation_id="UpdatePakDevice",
        path="/{pak_id:uuid}",
        guards=[requires_permission(PakPermission.UPDATE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def update_pak_device(
        self,
        request: Request[m.User, Any, Any],
        data: PakDeviceUpdate,
        pak_devices_service: NamedDependency[PakDeviceService],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],  # noqa: ARG002 - requested so the change commits
        pak_id: PakId,
    ) -> PakDevice:
        db_obj = await pak_devices_service.update_pak(pak_id, data.to_dict())
        await self._log_pak_action(
            request,
            audit_service,
            action="pak.updated",
            target=db_obj,
            details={"fields": [field for field in ("code", "kind") if getattr(data, field) is not msgspec.UNSET]},
        )

        return pak_devices_service.to_schema(
            db_obj,
            schema_type=PakDevice,
        )

    @post(
        operation_id="ActivatePakDevice",
        path="/{pak_id:uuid}/activate",
        status_code=HTTP_200_OK,
        guards=[requires_permission(PakPermission.SET_ACTIVE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def activate_pak_device(
        self,
        request: Request[m.User, Any, Any],
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        pak_id: PakId,
    ) -> PakDevice:
        return await self._set_active(
            request,
            pak_devices_service,
            hydra,
            audit_service,
            uow,
            pak_id,
            is_active=True,
        )

    @post(
        operation_id="DeactivatePakDevice",
        path="/{pak_id:uuid}/deactivate",
        status_code=HTTP_200_OK,
        guards=[requires_permission(PakPermission.SET_ACTIVE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def deactivate_pak_device(
        self,
        request: Request[m.User, Any, Any],
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        pak_id: PakId,
    ) -> PakDevice:
        return await self._set_active(
            request,
            pak_devices_service,
            hydra,
            audit_service,
            uow,
            pak_id,
            is_active=False,
        )

    async def _set_active(
        self,
        request: Request[m.User, Any, Any],
        pak_devices_service: PakDeviceService,
        hydra: HydraClient,
        audit_service: AuditLogService,
        uow: UnitOfWork,
        pak_id: UUID,
        *,
        is_active: bool,
    ) -> PakDevice:
        was_active = (await pak_devices_service.get(pak_id)).is_active
        db_obj = await pak_devices_service.set_active(
            pak_id,
            is_active=is_active,
            hydra=hydra,
            uow=uow,
        )

        if was_active != is_active:
            await self._log_pak_action(
                request,
                audit_service,
                action="pak.activated" if is_active else "pak.deactivated",
                target=db_obj,
            )

        return pak_devices_service.to_schema(
            db_obj,
            schema_type=PakDevice,
        )

    @post(
        operation_id="ArchivePakDevice",
        path="/{pak_id:uuid}/archive",
        status_code=HTTP_200_OK,
        guards=[requires_permission(PakPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def archive_pak_device(
        self,
        request: Request[m.User, Any, Any],
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        pak_id: PakId,
    ) -> PakDevice:
        return await self._set_archived(
            request,
            pak_devices_service,
            hydra,
            audit_service,
            uow,
            pak_id,
            archived=True,
        )

    @post(
        operation_id="RestorePakDevice",
        path="/{pak_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(PakPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_pak_device(
        self,
        request: Request[m.User, Any, Any],
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        pak_id: PakId,
    ) -> PakDevice:
        return await self._set_archived(
            request,
            pak_devices_service,
            hydra,
            audit_service,
            uow,
            pak_id,
            archived=False,
        )

    async def _set_archived(
        self,
        request: Request[m.User, Any, Any],
        pak_devices_service: PakDeviceService,
        hydra: HydraClient,
        audit_service: AuditLogService,
        uow: UnitOfWork,
        pak_id: UUID,
        *,
        archived: bool,
    ) -> PakDevice:
        was_archived = (await pak_devices_service.get(pak_id)).archived_at is not None
        db_obj = await pak_devices_service.set_archived(
            pak_id,
            archived=archived,
            hydra=hydra,
            uow=uow,
        )

        if was_archived != archived:
            await self._log_pak_action(
                request,
                audit_service,
                action="pak.archived" if archived else "pak.restored",
                target=db_obj,
            )

        return pak_devices_service.to_schema(
            db_obj,
            schema_type=PakDevice,
        )

    @get(
        operation_id="GetPakAccessKey",
        path="/{pak_id:uuid}/access-key",
        guards=[requires_permission(PakPermission.READ_ACCESS_KEY)],
        responses=error_responses(401, 403, 404),
    )
    async def get_pak_access_key(
        self,
        pak_devices_service: NamedDependency[PakDeviceService],
        pak_cipher: NamedDependency[PakAccessKeyCipher],
        pak_id: PakId,
    ) -> PakAccessKey:
        return PakAccessKey(
            access_key=await pak_devices_service.get_access_key(
                pak_id,
                cipher=pak_cipher,
            )
        )

    @post(
        operation_id="RotatePakAccessKey",
        path="/{pak_id:uuid}/access-key/rotate",
        status_code=HTTP_200_OK,
        guards=[requires_permission(PakPermission.ROTATE_ACCESS_KEY)],
        responses=error_responses(401, 403, 404, 409, 503),
    )
    async def rotate_pak_access_key(
        self,
        request: Request[m.User, Any, Any],
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        pak_cipher: NamedDependency[PakAccessKeyCipher],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        pak_id: PakId,
    ) -> PakAccessKey:
        target, access_key = await pak_devices_service.rotate_access_key(
            pak_id,
            hydra=hydra,
            cipher=pak_cipher,
            uow=uow,
        )
        await self._log_pak_action(
            request,
            audit_service,
            action="pak.access_key_rotated",
            target=target,
        )

        return PakAccessKey(access_key=access_key)

    @delete(
        operation_id="DeletePakDevice",
        path="/{pak_id:uuid}",
        status_code=HTTP_204_NO_CONTENT,
        guards=[requires_permission(PakPermission.DELETE)],
        responses=error_responses(401, 403, 404),
    )
    async def delete_pak_device(
        self,
        request: Request[m.User, Any, Any],
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        audit_service: NamedDependency[AuditLogService],
        uow: NamedDependency[UnitOfWork],
        pak_id: PakId,
    ) -> None:
        target = await pak_devices_service.delete_pak(
            pak_id,
            hydra=hydra,
            uow=uow,
        )
        await self._log_pak_action(
            request,
            audit_service,
            action="pak.deleted",
            target=target,
        )
