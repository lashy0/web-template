from __future__ import annotations

import asyncio
import sys
from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.auth.contracts import AuthSession, Identity
from app.auth.roles import Role
from app.core.config import Settings
from app.main import create_app
from app.modules.kg.models import KgStatus, KgUnit

_ALLOWED_ORIGIN = "https://admin.example"
_SESSION_COOKIE = "ory_kratos_session=opaque"


@pytest.fixture
def kg_client() -> Generator[tuple[FastAPI, TestClient]]:
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


def _kg(*, batch_id: UUID | None = None) -> KgUnit:
    now = datetime.now(UTC)
    return KgUnit(
        dev_eui="a1b2c3d4e5f60708",
        short_id="kg-000001",
        batch_id=batch_id or uuid4(),
        status=KgStatus.REGISTERED,
        created_at=now,
        updated_at=now,
    )


def _configure_principal(
    app: FastAPI,
    mocker: MockerFixture,
    service: SimpleNamespace,
    role: Role,
) -> UUID:
    user_id = uuid4()
    session = AuthSession(
        id=uuid4(),
        identity=Identity(id=uuid4(), login="manager", active=True),
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
            id=user_id,
            role=role,
            name="Manager",
            identity_login="manager",
        )
    )
    mocker.patch.object(app.state, "database", SimpleNamespace(session_factory=_SessionFactory()))
    mocker.patch.object(app.state, "kg_management", service)
    return user_id


def _headers() -> dict[str, str]:
    return {"origin": _ALLOWED_ORIGIN, "cookie": _SESSION_COOKIE}


@pytest.mark.api
def test_list_kg_serializes_items_and_forwards_filters(
    kg_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = kg_client
    kg = _kg()
    service = SimpleNamespace(list=AsyncMock(return_value=([kg], 1)))
    _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.get(
        f"/kg?q=a1b2&batch_id={kg.batch_id}&status=REGISTERED&page=2&page_size=10"
        "&sort=dev_eui&order=asc",
        headers=_headers(),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"][0]["dev_eui"] == kg.dev_eui
    assert response.json()["total"] == 1
    service.list.assert_awaited_once_with(
        q="a1b2",
        batch_id=kg.batch_id,
        status=KgStatus.REGISTERED,
        page=2,
        page_size=10,
        sort="dev_eui",
        order="asc",
    )


@pytest.mark.api
def test_get_kg_normalizes_dev_eui_and_returns_kg(
    kg_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = kg_client
    kg = _kg()
    service = SimpleNamespace(get=AsyncMock(return_value=kg))
    _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.get("/kg/A1B2C3D4E5F60708", headers=_headers())

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["batch_id"] == str(kg.batch_id)
    service.get.assert_awaited_once_with(dev_eui=kg.dev_eui)


@pytest.mark.api
def test_get_missing_kg_returns_not_found(
    kg_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = kg_client
    service = SimpleNamespace(get=AsyncMock(return_value=None))
    _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.get("/kg/a1b2c3d4e5f60708", headers=_headers())

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "kg_not_found"


@pytest.mark.api
def test_kg_read_requires_permission(
    kg_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = kg_client
    service = SimpleNamespace(list=AsyncMock())
    _configure_principal(app, mocker, service, Role.ENGINEER)

    response = client.get("/kg", headers=_headers())

    assert response.status_code == status.HTTP_403_FORBIDDEN
    service.list.assert_not_awaited()


@pytest.mark.api
def test_kg_rejects_an_invalid_dev_eui(
    kg_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = kg_client
    service = SimpleNamespace(get=AsyncMock())
    _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.get("/kg/invalid", headers=_headers())

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    service.get.assert_not_awaited()
