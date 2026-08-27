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
from app.auth.roles import Role
from app.core.config import Settings
from app.main import create_app
from app.modules.pak.exceptions import PakAlreadyExistsError, PakNotFoundError, PakProvisioningError
from app.modules.pak.models import PakDevice, PakDeviceKind

_ALLOWED_ORIGIN = "https://admin.example"
_SESSION_COOKIE = "ory_kratos_session=opaque"


@pytest.fixture
def pak_client() -> Generator[tuple[FastAPI, TestClient]]:
    app = create_app(Settings.model_validate({"BACKEND_CORS_ORIGINS": [_ALLOWED_ORIGIN]}))
    backend_options: dict[str, object] = {}
    if sys.platform == "win32":
        backend_options["loop_factory"] = asyncio.SelectorEventLoop
    with TestClient(app, backend_options=backend_options) as client:
        yield app, client


class _SessionFactory:
    def __call__(self) -> _SessionFactory:
        return self

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *args: object) -> None:
        return None


def _pak(*, pak_id: UUID | None = None) -> PakDevice:
    return PakDevice(
        id=pak_id or uuid4(),
        code="PAK-OTK-01",
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id="pak-test",
        encrypted_access_key="encrypted-value",
        is_active=True,
        last_seen_at=None,
        archived_at=None,
    )


def _configure_principal(
    app: FastAPI, mocker: MockerFixture, service: SimpleNamespace, role: Role
) -> UUID:
    user_id = uuid4()
    session = AuthSession(
        id=uuid4(),
        identity=Identity(id=uuid4(), login="operator", active=True),
        expires_at=datetime.now(UTC),
    )
    mocker.patch.object(
        app.state,
        "session_verifier",
        SimpleNamespace(verify_session=AsyncMock(return_value=session)),
    )
    repository = mocker.patch("app.api.auth_deps.UserRepository")
    repository.return_value.get_by_identity_id = AsyncMock(
        return_value=SimpleNamespace(
            id=user_id, role=role, name="Operator", identity_login="operator"
        )
    )
    mocker.patch.object(app.state, "database", SimpleNamespace(session_factory=_SessionFactory()))
    mocker.patch.object(app.state, "pak_management", service)
    return user_id


def _headers() -> dict[str, str]:
    return {"origin": _ALLOWED_ORIGIN, "cookie": _SESSION_COOKIE}


@pytest.mark.api
def test_create_returns_access_key_without_oauth_secret_field(
    pak_client: tuple[FastAPI, TestClient], mocker: MockerFixture
) -> None:
    app, client = pak_client
    pak = _pak()
    service = SimpleNamespace(create=AsyncMock(return_value=(pak, "new-access-key")))
    actor_id = _configure_principal(app, mocker, service, Role.ADMINISTRATOR)

    response = client.post(
        "/pak", headers=_headers(), json={"code": pak.code, "kind": pak.kind, "active": True}
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["access_key"] == "new-access-key"
    assert "credentials" not in response.json()
    assert "client_secret" not in response.text
    assert service.create.await_args.kwargs["actor"].user_id == actor_id


@pytest.mark.api
def test_pak_card_never_exposes_encrypted_access_key(
    pak_client: tuple[FastAPI, TestClient], mocker: MockerFixture
) -> None:
    app, client = pak_client
    pak = _pak()
    service = SimpleNamespace(get=AsyncMock(return_value=pak))
    _configure_principal(app, mocker, service, Role.ADMINISTRATOR)

    response = client.get(f"/pak/{pak.id}", headers=_headers())

    assert response.status_code == status.HTTP_200_OK
    assert "access_key" not in response.json()
    assert "encrypted_access_key" not in response.json()


@pytest.mark.api
def test_pak_list_never_exposes_access_key(
    pak_client: tuple[FastAPI, TestClient], mocker: MockerFixture
) -> None:
    app, client = pak_client
    pak = _pak()
    service = SimpleNamespace(list=AsyncMock(return_value=([pak], 1)))
    _configure_principal(app, mocker, service, Role.ADMINISTRATOR)

    response = client.get("/pak", headers=_headers())

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"][0]["code"] == pak.code
    assert "access_key" not in response.json()["items"][0]
    assert "encrypted_access_key" not in response.json()["items"][0]


@pytest.mark.api
def test_access_key_view_requires_dedicated_permission(
    pak_client: tuple[FastAPI, TestClient], mocker: MockerFixture
) -> None:
    app, client = pak_client
    service = SimpleNamespace(get_access_key=AsyncMock(return_value="not-returned"))
    _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.get(f"/pak/{uuid4()}/access-key", headers=_headers())

    assert response.status_code == status.HTTP_403_FORBIDDEN
    service.get_access_key.assert_not_awaited()


@pytest.mark.api
def test_rotate_access_key_uses_dedicated_service_method(
    pak_client: tuple[FastAPI, TestClient], mocker: MockerFixture
) -> None:
    app, client = pak_client
    pak_id = uuid4()
    service = SimpleNamespace(rotate_access_key=AsyncMock(return_value="rotated-access-key"))
    actor_id = _configure_principal(app, mocker, service, Role.ADMINISTRATOR)

    response = client.post(f"/pak/{pak_id}/access-key/rotate", headers=_headers(), json={})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"access_key": "rotated-access-key"}
    assert service.rotate_access_key.await_args.kwargs["pak_id"] == pak_id
    assert service.rotate_access_key.await_args.kwargs["actor"].user_id == actor_id


@pytest.mark.api
def test_update_pak_forwards_details_to_management_service(
    pak_client: tuple[FastAPI, TestClient], mocker: MockerFixture
) -> None:
    app, client = pak_client
    pak = _pak()
    service = SimpleNamespace(update=AsyncMock(return_value=pak))
    actor_id = _configure_principal(app, mocker, service, Role.ADMINISTRATOR)

    response = client.patch(
        f"/pak/{pak.id}",
        headers=_headers(),
        json={"code": "PAK-OTK-02", "kind": "ENGINEERING"},
    )

    assert response.status_code == status.HTTP_200_OK
    service.update.assert_awaited_once_with(
        actor=ANY, pak_id=pak.id, code="PAK-OTK-02", kind=PakDeviceKind.ENGINEERING
    )
    assert service.update.await_args.kwargs["actor"].user_id == actor_id


@pytest.mark.api
def test_active_and_archived_state_changes_are_forwarded(
    pak_client: tuple[FastAPI, TestClient], mocker: MockerFixture
) -> None:
    app, client = pak_client
    pak = _pak()
    service = SimpleNamespace(
        set_active=AsyncMock(return_value=pak), set_archived=AsyncMock(return_value=pak)
    )
    actor_id = _configure_principal(app, mocker, service, Role.ADMINISTRATOR)

    active_response = client.put(
        f"/pak/{pak.id}/active", headers=_headers(), json={"active": False}
    )
    archived_response = client.put(
        f"/pak/{pak.id}/archived", headers=_headers(), json={"archived": True}
    )

    assert active_response.status_code == status.HTTP_200_OK
    assert archived_response.status_code == status.HTTP_200_OK
    service.set_active.assert_awaited_once_with(actor=ANY, pak_id=pak.id, active=False)
    service.set_archived.assert_awaited_once_with(actor=ANY, pak_id=pak.id, archived=True)
    assert service.set_active.await_args.kwargs["actor"].user_id == actor_id
    assert service.set_archived.await_args.kwargs["actor"].user_id == actor_id


@pytest.mark.api
def test_delete_pak_forwards_requested_device(
    pak_client: tuple[FastAPI, TestClient], mocker: MockerFixture
) -> None:
    app, client = pak_client
    pak_id = uuid4()
    service = SimpleNamespace(delete=AsyncMock())
    actor_id = _configure_principal(app, mocker, service, Role.ADMINISTRATOR)

    response = client.delete(f"/pak/{pak_id}", headers=_headers())

    assert response.status_code == status.HTTP_204_NO_CONTENT
    service.delete.assert_awaited_once_with(actor=ANY, pak_id=pak_id)
    assert service.delete.await_args.kwargs["actor"].user_id == actor_id


@pytest.mark.api
@pytest.mark.parametrize(
    ("method", "path", "payload", "service_method", "error", "status_code", "code"),
    [
        pytest.param(
            "post",
            "/pak",
            {"code": "PAK-OTK-01", "kind": "OTK_LINE"},
            "create",
            PakProvisioningError,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "pak_provisioning_failed",
            id="provisioning-failed",
        ),
        pytest.param(
            "patch",
            f"/pak/{uuid4()}",
            {"code": "PAK-OTK-01"},
            "update",
            PakAlreadyExistsError,
            status.HTTP_409_CONFLICT,
            "pak_already_exists",
            id="code-conflict",
        ),
        pytest.param(
            "get",
            f"/pak/{uuid4()}",
            None,
            "get",
            PakNotFoundError,
            status.HTTP_404_NOT_FOUND,
            "pak_not_found",
            id="not-found",
        ),
    ],
)
def test_pak_errors_map_to_api_responses(
    pak_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
    method: str,
    path: str,
    payload: dict[str, str] | None,
    service_method: str,
    error: type[Exception],
    status_code: int,
    code: str,
) -> None:
    app, client = pak_client
    service = SimpleNamespace(**{service_method: AsyncMock(side_effect=error)})
    _configure_principal(app, mocker, service, Role.ADMINISTRATOR)

    request_kwargs: dict[str, object] = {"headers": _headers()}
    if payload is not None:
        request_kwargs["json"] = payload
    response = client.request(method, path, **request_kwargs)

    assert response.status_code == status_code
    assert response.json()["code"] == code
