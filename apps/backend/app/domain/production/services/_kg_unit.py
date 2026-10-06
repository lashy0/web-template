from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from advanced_alchemy.extensions.litestar import repository, service
from sqlalchemy import select

from app.db import models as m
from app.db.enums import PakDeviceKind, VerificationSessionStatus, VerificationStepStatus
from app.domain.production.schemas import (
    KgTimelineEvent,
    KgTimelineEventKind,
    KgTimelineSession,
    KgTimelineShipment,
    KgUnitAbp10Credentials,
    KgUnitAbp11Credentials,
    KgUnitCredentials,
    KgUnitOtaa10Credentials,
    KgUnitOtaa11Credentials,
    UserSummary,
)
from app.lib.lorawan import (
    Abp10Credentials,
    Abp11Credentials,
    Otaa10Credentials,
    Otaa11Credentials,
    generate_credentials,
)

_OTK_EVENTS = {
    VerificationSessionStatus.RUNNING: KgTimelineEventKind.OTK_RUNNING,
    VerificationSessionStatus.PASSED: KgTimelineEventKind.OTK_PASSED,
    VerificationSessionStatus.FAILED: KgTimelineEventKind.OTK_FAILED,
    VerificationSessionStatus.INCOMPLETE: KgTimelineEventKind.OTK_INCOMPLETE,
}


class KgUnitService(service.SQLAlchemyAsyncRepositoryService[m.KgUnit]):
    """Read access to the KG units registered by batches.

    Units change only through production processes, never directly by a user.
    """

    class Repo(repository.SQLAlchemyAsyncRepository[m.KgUnit]):
        """KG unit SQLAlchemy repository."""

        model_type = m.KgUnit
        id_attribute = "dev_eui"

    repository_type = Repo

    async def get_timeline(self, dev_eui: str) -> list[KgTimelineEvent]:
        """The life of the unit, oldest first.

        Only verifications on OTK-line PAKs are events: they set the OTK
        status, and the latest one, when the system closed it as incomplete,
        tells why the unit still waits for OTK. Receipts count units without
        DevEUIs, so they are not.

        Raises:
            advanced_alchemy.exceptions.NotFoundError: There is no such unit.
        """
        kg = await self.get(dev_eui)
        events = [
            _event(KgTimelineEventKind.REGISTERED, kg.created_at, actor=_summary(kg.batch.created_by)),
            *await self._otk_events(dev_eui),
        ]

        if kg.packed_at is not None:
            events.append(_event(KgTimelineEventKind.PACKED, kg.packed_at, actor=_summary(kg.packed_by)))

        events.extend(await self._shipment_events(dev_eui))
        # Stable, so an event keeps its place among others of the same moment.
        events.sort(key=lambda event: event.at)

        return events

    async def get_credentials(self, dev_eui: str) -> KgUnitCredentials:
        """The LoRaWAN identifiers and keys the unit was provisioned with.

        Keys are not stored: they are derived from the DevEUI as the batch's
        activation type and LoRaWAN version require. The generator also returns
        values the activation does not use (DevAddr for OTAA, AppKey for ABP);
        they are left out.

        Raises:
            advanced_alchemy.exceptions.NotFoundError: There is no such unit.
        """
        kg = await self.get(dev_eui)
        batch = kg.batch

        match generate_credentials(kg.dev_eui, batch.activation_type, batch.lorawan_version):
            case Otaa10Credentials() as keys:
                return KgUnitOtaa10Credentials(dev_eui=kg.dev_eui, join_eui=batch.join_eui, app_key=keys.app_key)
            case Otaa11Credentials() as keys:
                return KgUnitOtaa11Credentials(
                    dev_eui=kg.dev_eui,
                    join_eui=batch.join_eui,
                    app_key=keys.app_key,
                    nwk_key=keys.nwk_key,
                )
            case Abp10Credentials() as keys:
                return KgUnitAbp10Credentials(
                    dev_eui=kg.dev_eui,
                    dev_addr=keys.dev_addr,
                    nwk_s_key=keys.nwk_s_key,
                    app_s_key=keys.app_s_key,
                )
            case Abp11Credentials() as keys:
                return KgUnitAbp11Credentials(
                    dev_eui=kg.dev_eui,
                    dev_addr=keys.dev_addr,
                    f_nwk_s_int_key=keys.f_nwk_s_int_key,
                    s_nwk_s_int_key=keys.s_nwk_s_int_key,
                    nwk_s_enc_key=keys.nwk_s_enc_key,
                    app_s_key=keys.app_s_key,
                )

    async def _otk_events(self, dev_eui: str) -> list[KgTimelineEvent]:
        db = self.repository.session
        attempts = list(
            await db.scalars(
                select(m.VerificationSession)
                .where(
                    m.VerificationSession.dev_eui == dev_eui,
                    m.VerificationSession.pak_kind == PakDeviceKind.OTK_LINE,
                )
                .order_by(m.VerificationSession.started_at)
            )
        )
        latest = attempts[-1] if attempts else None
        # Aborted and incomplete sessions did not change the unit; only the
        # latest attempt, when the system closed it, says why OTK still waits.
        sessions = [
            item
            for item in attempts
            if item.status in _OTK_EVENTS
            and (item.status is not VerificationSessionStatus.INCOMPLETE or item is latest)
        ]
        failed_checks: defaultdict[UUID, list[str]] = defaultdict(list)
        failed = [item.id for item in sessions if item.status is VerificationSessionStatus.FAILED]

        if failed:
            for session_id, label in await db.execute(
                select(m.VerificationStep.session_id, m.VerificationStep.check_label)
                .where(
                    m.VerificationStep.session_id.in_(failed),
                    m.VerificationStep.status == VerificationStepStatus.FAILED,
                )
                .order_by(m.VerificationStep.step_no)
            ):
                failed_checks[session_id].append(label)

        return [
            _event(
                _OTK_EVENTS[item.status],
                _otk_event_at(item),
                session=KgTimelineSession(
                    id=item.id,
                    pak_code=item.pak.code,
                    slot_no=item.slot_no,
                    firmware_version=item.firmware_version,
                    completed_steps=item.completed_steps,
                    total_steps=item.total_steps,
                    failed_checks=failed_checks[item.id],
                ),
            )
            for item in sessions
        ]

    async def _shipment_events(self, dev_eui: str) -> list[KgTimelineEvent]:
        rows = await self.repository.session.execute(
            select(m.BatchShipmentItem.created_at, m.BatchShipment)
            .join(m.BatchShipment, m.BatchShipment.id == m.BatchShipmentItem.shipment_id)
            .where(m.BatchShipmentItem.dev_eui == dev_eui)
        )
        events: list[KgTimelineEvent] = []

        for added_at, shipment in rows.tuples():
            summary = KgTimelineShipment(id=shipment.id, number=shipment.number)

            if shipment.completed_at is not None:
                events.append(_event(KgTimelineEventKind.SHIPPED, shipment.completed_at, shipment=summary))

                if shipment.voided_at is not None:
                    events.append(_event(KgTimelineEventKind.SHIPMENT_VOIDED, shipment.voided_at, shipment=summary))
            # A shipment voided before completion never moved the unit.
            elif shipment.voided_at is None:
                events.append(_event(KgTimelineEventKind.SHIPMENT_ADDED, added_at, shipment=summary))

        return events


def _event(
    kind: KgTimelineEventKind,
    at: datetime,
    *,
    actor: UserSummary | None = None,
    session: KgTimelineSession | None = None,
    shipment: KgTimelineShipment | None = None,
) -> KgTimelineEvent:
    return KgTimelineEvent(kind=kind, at=at, actor=actor, session=session, shipment=shipment)


def _otk_event_at(item: m.VerificationSession) -> datetime:
    """When an OTK session happened in the timeline.

    A running session is an event from its start, one the system closed from
    the PAK's last report, and one the PAK finished from its end.
    """
    if item.status is VerificationSessionStatus.INCOMPLETE:
        return item.last_activity_at

    return item.completed_at or item.started_at


def _summary(user: m.User | None) -> UserSummary | None:
    return None if user is None else UserSummary(id=user.id, name=user.name)
