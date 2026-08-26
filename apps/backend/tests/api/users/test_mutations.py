from __future__ import annotations

import asyncio
import sys
from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.auth.contracts import AuthSession, Identity
from app.auth.exceptions import (
    IdentityAlreadyExistsError,
    IdentityNotFoundError,
    UserProvisioningError,
)
from app.auth.roles import Role
from app.core.config import Settings
from app.main import create_app
from app.modules.users.models import User

_ALLOWED_ORIGIN = "https://admin.example"
_SESSION_COOKIE = "ory_kratos_session=opaque"


@pytest.fixture
def mutation_client() -> Generator[tuple[FastAPI, TestClient]]:
    app = create_app(Settings.model_validate({"BACKEND_CORS_ORIGINS": [_ALLOWED_ORIGIN]}))
    backend_options: dict[str, object] = {}
    if sys.platform == "win32":
        backend_options["loop_factory"] = asyncio.SelectorEventLoop

    with TestClient(app, backend_options=backend_options) as client:
        yield app, client


def _user(*, user_id: UUID | None = None, login: str = "alice") -> User:
    return User(
        id=user_id or uuid4(),
        identity_id=uuid4(),
        name="Alice Smith",
        role=Role.MANAGER,
        identity_login=login,
        auth_state="active",
        auth_state_synced_at=datetime.now(UTC),
        archived_at=None,
    )


def _configure_administrator(
    app: FastAPI,
    mocker: MockerFixture,
    service: SimpleNamespace,
) -> UUID:
    actor_user_id = uuid4()
    session = AuthSession(
        id=uuid4(),
        identity=Identity(id=uuid4(), login="administrator", active=True),
        expires_at=datetime.now(UTC),
    )
    verifier = SimpleNamespace(verify_session=AsyncMock(return_value=session))
    repository = mocker.patch("app.api.auth_deps.UserRepository")
    repository.return_value.get_by_identity_id = AsyncMock(
        return_value=SimpleNamespace(
            id=actor_user_id,
            role=Role.ADMINISTRATOR,
            name="Administrator",
            identity_login="administrator",
        )
    )
    mocker.patch.object(app.state, "session_verifier", verifier)
    mocker.patch.object(app.state, "database", SimpleNamespace(session_factory=_SessionFactory()))
    mocker.patch.object(app.state, "user_management", service)
    return actor_user_id


class _SessionFactory:
    def __call__(self) -> _SessionFactory:
        return self

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *args: object) -> None:
        return None


def _headers() -> dict[str, str]:
    return {"origin": _ALLOWED_ORIGIN, "cookie": _SESSION_COOKIE}


@pytest.mark.api
def test_create_user_forwards_valid_payload_to_user_management(
    mutation_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = mutation_client
    created = _user()
    service = SimpleNamespace(create=AsyncMock(return_value=created))
    actor_user_id = _configure_administrator(app, mocker, service)

    response = client.post(
        "/users",
        headers=_headers(),
        json={
            "name": "Alice Smith",
            "role": "manager",
            "login": "alice",
            "password": "correct-horse-battery-staple",
            "active": True,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] == str(created.id)
    call = service.create.await_args.kwargs
    assert call["actor"].user_id == actor_user_id
    assert call["name"] == "Alice Smith"
    assert call["role"] is Role.MANAGER
    assert call["login"] == "alice"
    assert call["password"] == "correct-horse-battery-staple"
    assert call["active"] is True


@pytest.mark.api
def test_create_user_maps_failed_provisioning_to_service_unavailable(
    mutation_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = mutation_client
    service = SimpleNamespace(create=AsyncMock(side_effect=UserProvisioningError))
    _configure_administrator(app, mocker, service)

    response = client.post(
        "/users",
        headers=_headers(),
        json={
            "name": "Alice Smith",
            "role": "manager",
            "login": "alice",
            "password": "correct-horse-battery-staple",
            "active": True,
        },
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["code"] == "user_provisioning_failed"


@pytest.mark.api
def test_update_user_forwards_name_role_and_login(
    mutation_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = mutation_client
    target = _user()
    service = SimpleNamespace(update=AsyncMock(return_value=target))
    actor_user_id = _configure_administrator(app, mocker, service)

    response = client.patch(
        f"/users/{target.id}",
        headers=_headers(),
        json={"login": "alice.updated", "name": "Alice Updated", "role": "engineer"},
    )

    assert response.status_code == status.HTTP_200_OK
    service.update.assert_awaited_once_with(
        actor=ANY,
        user_id=target.id,
        login="alice.updated",
        name="Alice Updated",
        role=Role.ENGINEER,
    )
    assert service.update.await_args.kwargs["actor"].user_id == actor_user_id


@pytest.mark.api
def test_update_user_maps_login_conflict_to_client_error(
    mutation_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = mutation_client
    target = _user()
    service = SimpleNamespace(update=AsyncMock(side_effect=IdentityAlreadyExistsError))
    _configure_administrator(app, mocker, service)

    response = client.patch(
        f"/users/{target.id}",
        headers=_headers(),
        json={"login": "alice.updated"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "login_already_exists"
    service.update.assert_awaited_once()


@pytest.mark.api
def test_update_user_maps_missing_user_to_not_found(
    mutation_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = mutation_client
    service = SimpleNamespace(update=AsyncMock(side_effect=IdentityNotFoundError))
    _configure_administrator(app, mocker, service)

    response = client.patch(
        f"/users/{uuid4()}",
        headers=_headers(),
        json={"name": "Unknown User"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "user_not_found"
    service.update.assert_awaited_once()


@pytest.mark.api
def test_update_active_forwards_requested_state(
    mutation_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = mutation_client
    target = _user()
    target.auth_state = "inactive"
    service = SimpleNamespace(set_active=AsyncMock(return_value=target))
    actor_user_id = _configure_administrator(app, mocker, service)

    response = client.put(
        f"/users/{target.id}/active",
        headers=_headers(),
        json={"active": False},
    )

    assert response.status_code == status.HTTP_200_OK
    service.set_active.assert_awaited_once_with(actor=ANY, user_id=target.id, active=False)
    assert service.set_active.await_args.kwargs["actor"].user_id == actor_user_id


@pytest.mark.api
def test_update_archived_forwards_requested_state(
    mutation_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = mutation_client
    target = _user()
    service = SimpleNamespace(set_archived=AsyncMock(return_value=target))
    actor_user_id = _configure_administrator(app, mocker, service)

    response = client.put(
        f"/users/{target.id}/archived",
        headers=_headers(),
        json={"archived": True},
    )

    assert response.status_code == status.HTTP_200_OK
    service.set_archived.assert_awaited_once_with(actor=ANY, user_id=target.id, archived=True)
    assert service.set_archived.await_args.kwargs["actor"].user_id == actor_user_id


@pytest.mark.api
def test_delete_user_forwards_requested_user(
    mutation_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = mutation_client
    target = _user()
    service = SimpleNamespace(delete=AsyncMock())
    actor_user_id = _configure_administrator(app, mocker, service)

    response = client.delete(f"/users/{target.id}", headers=_headers())

    assert response.status_code == status.HTTP_204_NO_CONTENT
    service.delete.assert_awaited_once_with(actor=ANY, user_id=target.id)
    assert service.delete.await_args.kwargs["actor"].user_id == actor_user_id
