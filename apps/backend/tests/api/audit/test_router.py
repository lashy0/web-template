from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.auth.contracts import AuthSession, Identity
from app.auth.roles import Role
from app.modules.audit.models import AuditEvent


class _SessionFactory:
    def __call__(self) -> _SessionFactory:
        return self

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *args: object) -> None:
        return None


def _configure_authenticated_request(app: FastAPI, mocker: MockerFixture, *, role: Role) -> None:
    session = AuthSession(
        id=uuid4(),
        identity=Identity(id=uuid4(), login="alice", active=True),
        expires_at=datetime.now(UTC),
    )
    repository = mocker.patch("app.api.auth_deps.UserRepository")
    repository.return_value.get_by_identity_id = AsyncMock(
        return_value=SimpleNamespace(id=uuid4(), role=role, name="Alice", identity_login="alice")
    )
    mocker.patch.object(
        app.state,
        "session_verifier",
        SimpleNamespace(verify_session=AsyncMock(return_value=session)),
    )
    mocker.patch.object(app.state, "database", SimpleNamespace(session_factory=_SessionFactory()))


@pytest.mark.api
def test_administrator_can_list_audit_events(
    app: FastAPI, client: TestClient, api_prefix: str, mocker: MockerFixture
) -> None:
    _configure_authenticated_request(app, mocker, role=Role.ADMINISTRATOR)
    event = AuditEvent(
        id=uuid4(),
        created_at=datetime.now(UTC),
        actor_type="user",
        actor_id=str(uuid4()),
        actor_display_name="Alice",
        actor_identifier="alice",
        action="user.created",
        entity_type="user",
        entity_id="user-42",
        entity_display_name="Bob",
        entity_identifier="bob",
    )
    repository = mocker.patch("app.modules.audit.router.AuditRepository")
    repository.return_value.search = AsyncMock(return_value=([event], 1))

    response = client.get(
        f"{api_prefix}/audit?entity_type=user&page=2&page_size=10",
        headers={"cookie": "ory_kratos_session=opaque"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"][0]["actor_type"] == "user"
    assert response.json()["items"][0]["actor_id"] == event.actor_id
    assert response.json()["items"][0]["actor_display_name"] == "Alice"
    assert response.json()["items"][0]["actor_identifier"] == "alice"
    assert response.json()["items"][0]["entity_display_name"] == "Bob"
    assert response.json()["items"][0]["entity_identifier"] == "bob"
    repository.return_value.search.assert_awaited_once_with(
        created_from=None,
        created_to=None,
        entity_type=["user"],
        order="desc",
        page=2,
        page_size=10,
        sort="created_at",
    )


@pytest.mark.api
def test_audit_list_forwards_the_selected_sort(
    app: FastAPI, client: TestClient, api_prefix: str, mocker: MockerFixture
) -> None:
    _configure_authenticated_request(app, mocker, role=Role.ADMINISTRATOR)
    repository = mocker.patch("app.modules.audit.router.AuditRepository")
    repository.return_value.search = AsyncMock(return_value=([], 0))

    response = client.get(
        f"{api_prefix}/audit?entity_type=user&sort=actor_display_name&order=asc",
        headers={"cookie": "ory_kratos_session=opaque"},
    )

    assert response.status_code == status.HTTP_200_OK
    repository.return_value.search.assert_awaited_once_with(
        created_from=None,
        created_to=None,
        entity_type=["user"],
        order="asc",
        page=1,
        page_size=25,
        sort="actor_display_name",
    )


@pytest.mark.api
def test_audit_list_forwards_the_selected_period(
    app: FastAPI, client: TestClient, api_prefix: str, mocker: MockerFixture
) -> None:
    _configure_authenticated_request(app, mocker, role=Role.ADMINISTRATOR)
    repository = mocker.patch("app.modules.audit.router.AuditRepository")
    repository.return_value.search = AsyncMock(return_value=([], 0))

    response = client.get(
        f"{api_prefix}/audit?created_from=2026-08-18T00:00:00Z&created_to=2026-08-26T00:00:00Z",
        headers={"cookie": "ory_kratos_session=opaque"},
    )

    assert response.status_code == status.HTTP_200_OK
    repository.return_value.search.assert_awaited_once_with(
        created_from=datetime(2026, 8, 18, tzinfo=UTC),
        created_to=datetime(2026, 8, 26, tzinfo=UTC),
        entity_type=None,
        order="desc",
        page=1,
        page_size=25,
        sort="created_at",
    )


@pytest.mark.api
def test_non_administrator_cannot_list_audit_events(
    app: FastAPI, client: TestClient, api_prefix: str, mocker: MockerFixture
) -> None:
    _configure_authenticated_request(app, mocker, role=Role.MANAGER)
    repository = mocker.patch("app.modules.audit.router.AuditRepository")

    response = client.get(f"{api_prefix}/audit", headers={"cookie": "ory_kratos_session=opaque"})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    repository.assert_not_called()


@pytest.mark.api
def test_audit_list_accepts_multiple_entity_types(
    app: FastAPI, client: TestClient, api_prefix: str, mocker: MockerFixture
) -> None:
    _configure_authenticated_request(app, mocker, role=Role.ADMINISTRATOR)
    repository = mocker.patch("app.modules.audit.router.AuditRepository")
    repository.return_value.search = AsyncMock(return_value=([], 0))

    response = client.get(
        f"{api_prefix}/audit?entity_type=defect_group&entity_type=defect_type",
        headers={"cookie": "ory_kratos_session=opaque"},
    )

    assert response.status_code == status.HTTP_200_OK
    repository.return_value.search.assert_awaited_once_with(
        created_from=None,
        created_to=None,
        entity_type=["defect_group", "defect_type"],
        order="desc",
        page=1,
        page_size=25,
        sort="created_at",
    )
