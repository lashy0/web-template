"""Machine API through which a PAK reads its own registration."""

from __future__ import annotations

from litestar import Controller, get
from litestar.di import NamedDependency, Provide

from app.db import models as m
from app.domain.pak.deps import provide_current_pak, provide_pak_devices_service
from app.domain.pak.schemas import MachinePak
from app.domain.pak.services import PakDeviceService
from app.lib.openapi import error_responses


class MachinePakController(Controller):
    """The calling PAK, authenticated by its Hydra access token."""

    tags = ["PAK machine API"]  # noqa: RUF012
    path = "/machine/pak"
    opt = {"exclude_from_auth": True}  # noqa: RUF012 - authenticated by `current_pak` instead
    dependencies = {  # noqa: RUF012
        "pak_devices_service": Provide(provide_pak_devices_service),
        "current_pak": Provide(provide_current_pak),
    }

    @get(
        operation_id="GetMachinePak",
        path="",
        responses=error_responses(401, 403),
    )
    async def get_machine_pak(
        self,
        current_pak: NamedDependency[m.PakDevice],
        pak_devices_service: NamedDependency[PakDeviceService],
    ) -> MachinePak:
        """Return the calling PAK's code and kind, for the PAK to show them."""
        return pak_devices_service.to_schema(current_pak, schema_type=MachinePak)
