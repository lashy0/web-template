"""Machine API through which a PAK reads what to write into a KG unit."""

from __future__ import annotations

from typing import Annotated

from litestar import Controller, get
from litestar.datastructures import CacheControlHeader
from litestar.di import NamedDependency, Provide
from litestar.params import Parameter

from app.db import models as m
from app.domain.pak.deps import provide_current_pak, provide_pak_devices_service
from app.domain.quality.schemas import MachineKgProvisioning
from app.domain.quality.services import VerificationSessionService
from app.lib.deps import create_service_provider
from app.lib.lorawan import normalize_dev_eui
from app.lib.openapi import error_responses

DevEui = Annotated[
    str,
    Parameter(title="DevEUI", description="The KG unit: 16 hexadecimal characters, any case."),
]


class MachineKgKeysController(Controller):
    """Keys of KG units for the calling PAK, authenticated by its Hydra access token."""

    tags = ["PAK machine API"]  # noqa: RUF012
    path = "/machine/kg/units"
    opt = {"exclude_from_auth": True}  # noqa: RUF012 - authenticated by `current_pak` instead
    dependencies = {  # noqa: RUF012
        "pak_devices_service": Provide(provide_pak_devices_service),
        "current_pak": Provide(provide_current_pak),
        "verification_sessions_service": Provide(create_service_provider(VerificationSessionService)),
    }

    @get(
        operation_id="GetMachineKgKeys",
        path="/{dev_eui:str}/keys",
        responses=error_responses(401, 403, 404, 409),
        # The keys must not stay in a proxy cache.
        cache_control=CacheControlHeader(no_store=True),
    )
    async def get_machine_kg_keys(
        self,
        current_pak: NamedDependency[m.PakDevice],
        verification_sessions_service: NamedDependency[VerificationSessionService],
        dev_eui: DevEui,
    ) -> MachineKgProvisioning:
        """The LoRaWAN keys of the unit and the multicast groups of its batch; see ``docs/domain/verification.md``."""
        return await verification_sessions_service.get_provisioning(current_pak, normalize_dev_eui(dev_eui))
