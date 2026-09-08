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
from app.modules.batch.models import Batch
from app.modules.kg.models import KgDevEuiPrefix, KgStatus, KgUnit, KgVersion

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
    batch = Batch(id=batch_id or uuid4(), name="August production")
    return KgUnit(
        dev_eui="a1b2c3d4e5f60708",
        short_id="kg-000001",
        batch_id=batch.id,
        batch=batch,
        status=KgStatus.REGISTERED,
        created_at=now,
        updated_at=now,
    )


def _prefix() -> KgDevEuiPrefix:
    return KgDevEuiPrefix(
        prefix="a1b2c3d4e5",
        short_code="kg",
        name="Основной",
        created_at=datetime.now(UTC),
    )


def _version() -> KgVersion:
    now = datetime.now(UTC)
    return KgVersion(
        id=uuid4(),
        code="KG-1",
        name="Первая версия",
        description="Описание",
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
    assert response.json()["items"][0]["batch"] == {"id": str(kg.batch_id), "name": kg.batch.name}
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
def test_list_dev_eui_prefixes_uses_the_prefix_route(
    kg_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = kg_client
    service = SimpleNamespace(list=AsyncMock())
    _configure_principal(app, mocker, service, Role.ADMINISTRATOR)
    prefix = _prefix()
    prefix_service = SimpleNamespace(list=AsyncMock(return_value=([(prefix, 4)], 1)))
    mocker.patch.object(app.state, "kg_dev_eui_prefix_management", prefix_service)

    response = client.get("/kg/dev-eui-prefixes", headers=_headers())

    assert response.status_code == status.HTTP_200_OK
    item = response.json()["items"][0]
    assert item["prefix"] == "a1b2c3d4e5"
    assert item["short_code"] == "kg"
    assert item["name"] == "Основной"
    assert item["batch_count"] == 4
    assert item["created_at"].endswith("Z")
    assert response.json()["total"] == 1
    prefix_service.list.assert_awaited_once_with(
        q=None,
        archived=False,
        page=1,
        page_size=25,
        sort="prefix",
        order="asc",
    )


@pytest.mark.api
def test_list_kg_versions_is_not_captured_by_the_dev_eui_route(
    kg_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = kg_client
    service = SimpleNamespace(list=AsyncMock())
    _configure_principal(app, mocker, service, Role.ADMINISTRATOR)
    version = _version()
    version_service = SimpleNamespace(list=AsyncMock(return_value=([(version, 4)], 1)))
    mocker.patch.object(app.state, "kg_version_management", version_service)

    response = client.get("/kg/versions", headers=_headers())

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"][0]["code"] == "KG-1"
    assert response.json()["items"][0]["batch_count"] == 4
    version_service.list.assert_awaited_once_with(
        q=None,
        archived=False,
        page=1,
        page_size=25,
        sort_by="code",
        sort_order="asc",
    )


@pytest.mark.api
@pytest.mark.parametrize(
    ("method", "url", "payload", "operation", "expected_status"),
    [
        pytest.param(
            "post",
            "/kg/versions",
            {"code": "KG-1", "name": "Первая версия"},
            "create",
            status.HTTP_201_CREATED,
            id="create-version",
        ),
        pytest.param(
            "patch",
            "/kg/versions/{id}",
            {"name": "Обновлённая версия"},
            "update",
            status.HTTP_200_OK,
            id="update-version",
        ),
        pytest.param(
            "put",
            "/kg/versions/{id}/archived",
            {"archived": True},
            "set_archived",
            status.HTTP_200_OK,
            id="archive-version",
        ),
    ],
)
def test_kg_version_mutations_return_actual_batch_count(
    kg_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
    method: str,
    url: str,
    payload: dict[str, object],
    operation: str,
    expected_status: int,
) -> None:
    app, client = kg_client
    version = _version()
    service = SimpleNamespace(
        create=AsyncMock(return_value=version),
        update=AsyncMock(return_value=version),
        set_archived=AsyncMock(return_value=version),
        count_batches=AsyncMock(return_value=4),
    )
    _configure_principal(app, mocker, SimpleNamespace(), Role.ADMINISTRATOR)
    mocker.patch.object(app.state, "kg_version_management", service)

    response = getattr(client, method)(
        url.format(id=version.id),
        headers=_headers(),
        json=payload,
    )

    assert response.status_code == expected_status
    assert response.json()["batch_count"] == 4
    service.count_batches.assert_awaited_once_with(version.id)
    getattr(service, operation).assert_awaited_once()


@pytest.mark.api
@pytest.mark.parametrize(
    ("method", "url", "payload", "operation", "expected_status"),
    [
        pytest.param(
            "post",
            "/kg/dev-eui-prefixes",
            {"prefix": "a1b2c3d4e5", "short_code": "kg", "name": "Основной"},
            "create",
            status.HTTP_201_CREATED,
            id="create-prefix",
        ),
        pytest.param(
            "patch",
            "/kg/dev-eui-prefixes/a1b2c3d4e5",
            {"name": "Резервный"},
            "update",
            status.HTTP_200_OK,
            id="update-prefix",
        ),
        pytest.param(
            "put",
            "/kg/dev-eui-prefixes/a1b2c3d4e5/archived",
            {"archived": True},
            "set_archived",
            status.HTTP_200_OK,
            id="archive-prefix",
        ),
    ],
)
def test_prefix_mutations_return_actual_batch_count(
    kg_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
    method: str,
    url: str,
    payload: dict[str, object],
    operation: str,
    expected_status: int,
) -> None:
    app, client = kg_client
    prefix = _prefix()
    service = SimpleNamespace(
        create=AsyncMock(return_value=prefix),
        update=AsyncMock(return_value=prefix),
        set_archived=AsyncMock(return_value=prefix),
        count_batches=AsyncMock(return_value=4),
    )
    _configure_principal(app, mocker, SimpleNamespace(), Role.ADMINISTRATOR)
    mocker.patch.object(app.state, "kg_dev_eui_prefix_management", service)

    response = getattr(client, method)(url, headers=_headers(), json=payload)

    assert response.status_code == expected_status
    assert response.json()["batch_count"] == 4
    service.count_batches.assert_awaited_once_with(prefix.prefix)
    getattr(service, operation).assert_awaited_once()


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
    _configure_principal(app, mocker, service, Role.PACKER)

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
