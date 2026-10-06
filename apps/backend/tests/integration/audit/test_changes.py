"""The change recorder's request dependencies over HTTP, PostgreSQL and memory channels."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any, Literal, cast
from uuid import uuid4

import pytest
from advanced_alchemy.exceptions import RepositoryError
from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
from litestar import Litestar, Request, post
from litestar.di import NamedDependency, Provide
from litestar.params import FromPath
from litestar.testing import AsyncTestClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import models as m
from app.db.enums import UserRole
from app.domain.accounts.deps import provide_users_service
from app.domain.accounts.events import UserChanged
from app.domain.accounts.schemas import ProfileUpdate
from app.domain.accounts.services import UserService
from app.domain.audit.changes import ChangeRecorder
from app.domain.audit.deps import provide_audit_log_service, provide_change_recorder
from app.lib.exceptions import ApplicationError, exception_group_to_http_response, exception_to_http_response
from app.lib.realtime import Realtime, ResyncSubscriber, create_realtime
from app.lib.uow import provide_uow, unit_of_work

pytestmark = [pytest.mark.anyio, pytest.mark.integration]

type Outcome = Literal["record", "announce", "handler-error", "commit-error"]


@post("/{outcome:str}", status_code=200)
async def _change_profile(
    request: Request[m.User, Any, Any],
    users_service: NamedDependency[UserService],
    changes: NamedDependency[ChangeRecorder],
    outcome: FromPath[Outcome],
) -> None:
    user = await users_service.update_profile(request.user.id, ProfileUpdate(name="Changed Actor"))
    event = UserChanged(user_id=user.id)

    if outcome == "announce":
        changes.announce(event)
    else:
        await changes.record("user.updated", user, event=event, details={"name": user.name})

    if outcome == "handler-error":
        raise ApplicationError(detail="Handler failed after recording the change")

    if outcome == "commit-error":
        # The insert succeeds; PostgreSQL checks this foreign key only at commit.
        await users_service.repository.session.execute(
            text(
                "CREATE TEMP TABLE change_commit_failure ("
                "id integer PRIMARY KEY, parent_id integer REFERENCES change_commit_failure(id) "
                "DEFERRABLE INITIALLY DEFERRED) ON COMMIT DROP"
            )
        )
        await users_service.repository.session.execute(
            text("INSERT INTO change_commit_failure (id, parent_id) VALUES (1, 2)")
        )


@pytest.fixture(name="recorder_actor")
async def fx_recorder_actor(session: AsyncSession) -> m.User:
    user = m.User(
        identity_id=uuid4(),
        identity_login=f"recorder-{uuid4().hex[:8]}",
        identity_active=True,
        name="Original Actor",
        role=UserRole.ADMINISTRATOR,
    )

    async with unit_of_work(session):
        session.add(user)

    return user


@pytest.fixture(name="recorder_realtime")
def fx_recorder_realtime(recorder_actor: m.User) -> Realtime:
    return create_realtime(get_settings())


@pytest.fixture(name="changes_client")
async def fx_changes_client(
    recorder_actor: m.User,
    recorder_realtime: Realtime,
) -> AsyncGenerator[AsyncTestClient[Litestar]]:
    # This small app exercises the real providers without replacing any production route or service.
    alchemy = get_settings().db.get_config()

    async def authenticate(request: Request[m.User, Any, Any]) -> None:
        request.scope["user"] = recorder_actor

    def provide_realtime() -> Realtime:
        return recorder_realtime

    app = Litestar(
        route_handlers=[_change_profile],
        before_request=authenticate,
        dependencies={
            "users_service": Provide(provide_users_service),
            "audit_service": Provide(provide_audit_log_service),
            "changes": Provide(provide_change_recorder, sync_to_thread=False),
            "uow": Provide(provide_uow),
            "realtime": Provide(provide_realtime, sync_to_thread=False),
        },
        exception_handlers={
            ApplicationError: exception_to_http_response,
            RepositoryError: exception_to_http_response,
            ExceptionGroup: exception_group_to_http_response,
        },
        plugins=[SQLAlchemyPlugin(config=alchemy), recorder_realtime.channels],
    )

    async with AsyncTestClient(app) as client:
        try:
            yield client
        finally:
            client.blocking_portal.call(alchemy.get_engine().dispose)


@pytest.fixture(name="recorder_events")
async def fx_recorder_events(
    changes_client: AsyncTestClient[Litestar],
    recorder_realtime: Realtime,
) -> AsyncGenerator[ResyncSubscriber]:
    names = [recorder_realtime.channel(UserChanged.permission)]
    portal = changes_client.blocking_portal
    subscriber = cast("ResyncSubscriber", portal.call(recorder_realtime.channels.subscribe, names))

    try:
        yield subscriber
    finally:
        portal.call(recorder_realtime.channels.unsubscribe, subscriber, names)


async def test_record_commits_change_and_audit_with_request_metadata(
    changes_client: AsyncTestClient[Litestar],
    recorder_actor: m.User,
    recorder_events: ResyncSubscriber,
    session: AsyncSession,
) -> None:
    response = await changes_client.post("/record", headers={"user-agent": "recorder-test"})

    await session.refresh(recorder_actor)
    entry = await session.scalar(select(m.AuditLog))
    assert entry is not None
    assert (response.status_code, recorder_actor.name, entry.action, entry.target_id, entry.details) == (
        200,
        "Changed Actor",
        "user.updated",
        str(recorder_actor.id),
        {"name": "Changed Actor"},
    )
    assert (entry.actor_id, entry.actor_login, entry.actor_name, entry.user_agent) == (
        recorder_actor.id,
        recorder_actor.identity_login,
        "Original Actor",
        "recorder-test",
    )
    assert recorder_events.qsize == 1
    payload = changes_client.blocking_portal.call(recorder_events.get)
    assert payload is not None
    assert json.loads(payload) == {"type": "user.changed", "data": {"userId": str(recorder_actor.id)}}


@pytest.mark.parametrize(("outcome", "status_code"), [("handler-error", 500), ("commit-error", 409)])
async def test_failed_change_rolls_back_change_and_audit_without_an_event(
    changes_client: AsyncTestClient[Litestar],
    recorder_actor: m.User,
    recorder_events: ResyncSubscriber,
    session: AsyncSession,
    outcome: str,
    status_code: int,
) -> None:
    response = await changes_client.post(f"/{outcome}")

    await session.refresh(recorder_actor)
    entry = await session.scalar(select(m.AuditLog))
    assert (response.status_code, recorder_actor.name, entry, recorder_events.qsize) == (
        status_code,
        "Original Actor",
        None,
        0,
    )


async def test_announce_commits_change_without_an_audit_entry(
    changes_client: AsyncTestClient[Litestar],
    recorder_actor: m.User,
    recorder_events: ResyncSubscriber,
    session: AsyncSession,
) -> None:
    response = await changes_client.post("/announce")

    await session.refresh(recorder_actor)
    entry = await session.scalar(select(m.AuditLog))
    assert (response.status_code, recorder_actor.name, entry, recorder_events.qsize) == (
        200,
        "Changed Actor",
        None,
        1,
    )


async def test_recorder_uses_metadata_of_each_request(
    changes_client: AsyncTestClient[Litestar],
    session: AsyncSession,
) -> None:
    await changes_client.post("/record", headers={"user-agent": "first-request"})

    response = await changes_client.post("/record", headers={"user-agent": "second-request"})

    agents = await session.scalars(select(m.AuditLog.user_agent).order_by(m.AuditLog.created_at))
    assert (response.status_code, list(agents)) == (200, ["first-request", "second-request"])
