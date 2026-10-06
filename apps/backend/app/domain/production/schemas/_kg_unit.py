from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.db.enums import KgOtkStatus, KgState
from app.domain.production.schemas._batch import BatchKgVersion, UserSummary
from app.lib.lorawan import ActivationType, LoRaWanVersion
from app.lib.schema import CamelizedBaseStruct


class KgUnitBatch(CamelizedBaseStruct):
    id: UUID
    name: str


class KgUnitPak(CamelizedBaseStruct):
    id: UUID
    code: str


class KgUnitRunningOtk(CamelizedBaseStruct):
    """The verification of the unit running on an OTK-line PAK now."""

    id: UUID
    pak: KgUnitPak
    slot_no: int


class KgUnitShipment(CamelizedBaseStruct):
    """The completed shipment that shipped the unit."""

    id: UUID
    number: int
    completed_at: datetime


class KgUnit(CamelizedBaseStruct):
    dev_eui: str
    short_id: str
    state: KgState
    otk_status: KgOtkStatus
    """The result of the last finished OTK; a running one changes it only when it ends."""
    running_otk: KgUnitRunningOtk | None
    last_verification_at: datetime | None
    packed_at: datetime | None
    packed_by: UserSummary | None
    shipment: KgUnitShipment | None
    """Set while the unit is shipped; voiding the shipment clears it."""
    activation_type: ActivationType
    lorawan_version: LoRaWanVersion
    kg_version: BatchKgVersion | None
    """The KG version of the batch."""
    batch: KgUnitBatch
    created_at: datetime
    updated_at: datetime


class _KgUnitCredentials(CamelizedBaseStruct, tag_field="scheme"):
    """The LoRaWAN identifiers and keys of a unit, derived from its DevEUI on request.

    ``scheme`` names the activation type and LoRaWAN version of the batch, which
    decide the fields. Hex values are lower case.
    """

    dev_eui: str


class KgUnitOtaa10Credentials(_KgUnitCredentials, tag="otaa-1.0"):
    join_eui: str
    """The AppEUI of LoRaWAN 1.0."""
    app_key: str


class KgUnitOtaa11Credentials(_KgUnitCredentials, tag="otaa-1.1"):
    join_eui: str
    app_key: str
    nwk_key: str


class KgUnitAbp10Credentials(_KgUnitCredentials, tag="abp-1.0"):
    dev_addr: str
    nwk_s_key: str
    app_s_key: str


class KgUnitAbp11Credentials(_KgUnitCredentials, tag="abp-1.1"):
    dev_addr: str
    f_nwk_s_int_key: str
    s_nwk_s_int_key: str
    nwk_s_enc_key: str
    app_s_key: str


KgUnitCredentials = KgUnitOtaa10Credentials | KgUnitOtaa11Credentials | KgUnitAbp10Credentials | KgUnitAbp11Credentials


class KgOtkFilter(StrEnum):
    """A value of the KG units' OTK filter: a last OTK result, or an OTK running now."""

    NOT_VERIFIED = KgOtkStatus.NOT_VERIFIED.value
    PASSED = KgOtkStatus.PASSED.value
    FAILED = KgOtkStatus.FAILED.value
    RUNNING = "running"
    """On an OTK-line PAK now, whatever the last result."""


class KgTimelineEventKind(StrEnum):
    """What happened to a KG unit."""

    REGISTERED = "registered"
    """The batch registered the unit when it was created."""
    OTK_RUNNING = "otk_running"
    """A verification on an OTK-line PAK is running; the event is its start."""
    OTK_PASSED = "otk_passed"
    OTK_FAILED = "otk_failed"
    """A verification on an OTK-line PAK ended with this result."""
    OTK_INCOMPLETE = "otk_incomplete"
    """The latest verification on an OTK-line PAK was closed as incomplete; the event is the PAK's last report.

    It does not change the unit: it tells why the unit still waits for OTK.
    """
    PACKED = "packed"
    SHIPMENT_ADDED = "shipment_added"
    """The unit is in a shipment that is still open."""
    SHIPPED = "shipped"
    SHIPMENT_VOIDED = "shipment_voided"
    """A completed shipment of the unit was voided: the unit is packed again."""


class KgTimelineSession(CamelizedBaseStruct):
    """The verification behind an OTK event."""

    id: UUID
    pak_code: str
    slot_no: int
    firmware_version: str
    """The KG controller firmware the PAK reported when the verification started."""
    completed_steps: int
    total_steps: int
    failed_checks: list[str]
    """Labels of the failed steps in step order; empty unless the verification failed."""


class KgTimelineShipment(CamelizedBaseStruct):
    id: UUID
    number: int


class KgTimelineEvent(CamelizedBaseStruct):
    """One event in the life of a KG unit; the details match ``kind``."""

    kind: KgTimelineEventKind
    at: datetime
    actor: UserSummary | None
    """Who created the batch for ``registered``, who packed the unit for ``packed``."""
    session: KgTimelineSession | None
    """For ``otk_running``, ``otk_passed``, ``otk_failed`` and ``otk_incomplete``."""
    shipment: KgTimelineShipment | None
    """For ``shipment_added``, ``shipped`` and ``shipment_voided``."""
