"""PAK device controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from advanced_alchemy.extensions.litestar.providers import FieldNameType
from advanced_alchemy.service import schema_dump
from litestar import Controller, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter, SkipValidation
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.db.enums import PakDeviceKind
from app.domain.audit.changes import ChangeRecorder
from app.domain.pak.crypto import PakAccessKeyCipher
from app.domain.pak.deps import provide_pak_access_key_cipher
from app.domain.pak.events import PakChanged
from app.domain.pak.permissions import PakPermission
from app.domain.pak.schemas import (
    PakAccessKey,
    PakAccessKeyRotation,
    PakAccessKeyRotationMode,
    PakDevice,
    PakDeviceCreate,
    PakDeviceProvisioned,
    PakDeviceUpdate,
)
from app.domain.pak.services import PakDeviceService
from app.lib.audit import change_details, same_fields, snapshot
from app.lib.authorization import requires_permission
from app.lib.concurrency import update_changes
from app.lib.deps import create_service_dependencies
from app.lib.filters import create_active_filter_provider, provide_archived_filter
from app.lib.hydra import HydraClient
from app.lib.openapi import error_responses
from app.lib.uow import UnitOfWork

if TYPE_CHECKING:
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.service.pagination import OffsetPagination

PakId = Annotated[UUID, Parameter(title="PAK ID", description="The PAK device to act on.")]


_AUDIT_FIELDS = same_fields("code", "kind")
"""Fields the ``updated`` audit entries compare."""


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
            "in_fields": [FieldNameType(name="kind", type_hint=PakDeviceKind)],
        },
    )
    dependencies["archived_filter"] = Provide(provide_archived_filter, sync_to_thread=False)
    dependencies["active_filter"] = Provide(create_active_filter_provider("is_active"), sync_to_thread=False)
    dependencies["pak_cipher"] = Provide(provide_pak_access_key_cipher, sync_to_thread=False)

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
        active_filter: NamedDependency[SkipValidation[list[FilterTypes]]],
    ) -> OffsetPagination[PakDevice]:
        results, total = await pak_devices_service.get_many_and_count(*filters, *archived_filter, *active_filter)

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
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        pak_cipher: NamedDependency[PakAccessKeyCipher],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        data: PakDeviceCreate,
    ) -> PakDeviceProvisioned:
        db_obj, access_key = await pak_devices_service.create_pak(
            schema_dump(data),
            hydra=hydra,
            cipher=pak_cipher,
            uow=uow,
        )
        await changes.record(
            "pak.created",
            db_obj,
            event=PakChanged(pak_id=db_obj.id),
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
        data: PakDeviceUpdate,
        pak_devices_service: NamedDependency[PakDeviceService],
        changes: NamedDependency[ChangeRecorder],
        pak_id: PakId,
    ) -> PakDevice:
        before = snapshot(await pak_devices_service.get(pak_id), _AUDIT_FIELDS)
        db_obj = await pak_devices_service.update_pak(
            pak_id,
            update_changes(data),
            expected_updated_at=data.expected_updated_at,
        )

        if details := change_details(before, snapshot(db_obj, _AUDIT_FIELDS)):
            await changes.record(
                "pak.updated",
                db_obj,
                event=PakChanged(pak_id=db_obj.id),
                details=details,
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
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        pak_id: PakId,
    ) -> PakDevice:
        return await self._set_active(pak_devices_service, hydra, uow, changes, pak_id, is_active=True)

    @post(
        operation_id="DeactivatePakDevice",
        path="/{pak_id:uuid}/deactivate",
        status_code=HTTP_200_OK,
        guards=[requires_permission(PakPermission.SET_ACTIVE)],
        responses=error_responses(401, 403, 404, 409),
    )
    async def deactivate_pak_device(
        self,
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        pak_id: PakId,
    ) -> PakDevice:
        return await self._set_active(pak_devices_service, hydra, uow, changes, pak_id, is_active=False)

    @staticmethod
    async def _set_active(
        pak_devices_service: PakDeviceService,
        hydra: HydraClient,
        uow: UnitOfWork,
        changes: ChangeRecorder,
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
            await changes.record(
                "pak.activated" if is_active else "pak.deactivated",
                db_obj,
                event=PakChanged(pak_id=db_obj.id),
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
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        pak_id: PakId,
    ) -> PakDevice:
        return await self._set_archived(pak_devices_service, hydra, uow, changes, pak_id, archived=True)

    @post(
        operation_id="RestorePakDevice",
        path="/{pak_id:uuid}/restore",
        status_code=HTTP_200_OK,
        guards=[requires_permission(PakPermission.ARCHIVE)],
        responses=error_responses(401, 403, 404),
    )
    async def restore_pak_device(
        self,
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        pak_id: PakId,
    ) -> PakDevice:
        return await self._set_archived(pak_devices_service, hydra, uow, changes, pak_id, archived=False)

    @staticmethod
    async def _set_archived(
        pak_devices_service: PakDeviceService,
        hydra: HydraClient,
        uow: UnitOfWork,
        changes: ChangeRecorder,
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
            await changes.record(
                "pak.archived" if archived else "pak.restored",
                db_obj,
                event=PakChanged(pak_id=db_obj.id),
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
        data: PakAccessKeyRotation,
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        pak_cipher: NamedDependency[PakAccessKeyCipher],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        pak_id: PakId,
    ) -> PakAccessKey:
        target, access_key = await pak_devices_service.rotate_access_key(
            pak_id,
            hydra=hydra,
            cipher=pak_cipher,
            uow=uow,
            revoke_tokens=data.mode is PakAccessKeyRotationMode.IMMEDIATE,
        )
        await changes.record(
            "pak.access_key_rotated",
            target,
            event=PakChanged(pak_id=target.id),
            details={"mode": data.mode.value},
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
        pak_devices_service: NamedDependency[PakDeviceService],
        hydra: NamedDependency[HydraClient],
        uow: NamedDependency[UnitOfWork],
        changes: NamedDependency[ChangeRecorder],
        pak_id: PakId,
    ) -> None:
        target = await pak_devices_service.delete_pak(
            pak_id,
            hydra=hydra,
            uow=uow,
        )
        await changes.record("pak.deleted", target, event=PakChanged(pak_id=target.id))
