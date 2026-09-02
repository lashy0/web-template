from __future__ import annotations

import asyncio
import sys
from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.auth.contracts import AuthSession, Identity
from app.auth.roles import Role
from app.core.config import Settings
from app.main import create_app
from app.modules.defects.models import DefectGroup, DefectType

_ALLOWED_ORIGIN = "https://admin.example"
_SESSION_COOKIE = "ory_kratos_session=opaque"


@pytest.fixture
def defects_client() -> Generator[tuple[FastAPI, TestClient]]:
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


def _group() -> DefectGroup:
    now = datetime.now(UTC)
    return DefectGroup(
        id=uuid4(),
        code="POWER",
        name="Power supply",
        description="Power-related failures",
        archived_at=None,
        created_at=now,
        updated_at=now,
    )


def _type(group: DefectGroup) -> DefectType:
    now = datetime.now(UTC)
    return DefectType(
        id=uuid4(),
        group_id=group.id,
        code="VOLTAGE_LOW",
        name="Low voltage",
        description="Voltage is below the acceptable range.",
        possible_cause="Loose cable",
        engineer_action="Check the cable.",
        archived_at=None,
        created_at=now,
        updated_at=now,
    )


def _configure_principal(
    app: FastAPI,
    mocker: MockerFixture,
    service: SimpleNamespace,
    role: Role,
) -> None:
    session = AuthSession(
        id=uuid4(),
        identity=Identity(id=uuid4(), login="admin", active=True),
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
            id=uuid4(), role=role, name="Admin", identity_login="admin"
        )
    )
    mocker.patch.object(app.state, "database", SimpleNamespace(session_factory=_SessionFactory()))
    mocker.patch.object(app.state, "defect_management", service)


def _headers() -> dict[str, str]:
    return {"origin": _ALLOWED_ORIGIN, "cookie": _SESSION_COOKIE}


@pytest.mark.api
def test_list_groups_serializes_items_and_forwards_filters(
    defects_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = defects_client
    group = _group()
    service = SimpleNamespace(list_groups=AsyncMock(return_value=([group], 1)))
    _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.get(
        "/defects/groups?q=power&archived=false&page=2&page_size=10&sort=name&order=desc",
        headers=_headers(),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"][0]["id"] == str(group.id)
    assert response.json()["total"] == 1
    service.list_groups.assert_awaited_once_with(
        q="power",
        archived=False,
        page=2,
        page_size=10,
        sort="name",
        order="desc",
    )


@pytest.mark.api
def test_group_mutation_routes_forward_normalized_payloads(
    defects_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = defects_client
    group = _group()
    service = SimpleNamespace(
        create_group=AsyncMock(return_value=group),
        update_group=AsyncMock(return_value=group),
        set_group_archived=AsyncMock(return_value=group),
        delete_group=AsyncMock(),
    )
    _configure_principal(app, mocker, service, Role.ADMINISTRATOR)

    created = client.post(
        "/defects/groups",
        headers=_headers(),
        json={"code": " POWER ", "name": " Power supply ", "description": "   "},
    )
    updated = client.patch(
        f"/defects/groups/{group.id}",
        headers=_headers(),
        json={"name": " Backup power ", "description": "  Secondary circuit  "},
    )
    archived = client.put(
        f"/defects/groups/{group.id}/archived", headers=_headers(), json={"archived": True}
    )
    deleted = client.delete(f"/defects/groups/{group.id}", headers=_headers())

    assert [response.status_code for response in (created, updated, archived, deleted)] == [
        status.HTTP_201_CREATED,
        status.HTTP_200_OK,
        status.HTTP_200_OK,
        status.HTTP_204_NO_CONTENT,
    ]
    service.create_group.assert_awaited_once_with(
        actor=ANY, code="POWER", name="Power supply", description=None
    )
    service.update_group.assert_awaited_once_with(
        actor=ANY,
        group_id=group.id,
        updates={"name": "Backup power", "description": "Secondary circuit"},
    )
    service.set_group_archived.assert_awaited_once_with(actor=ANY, group_id=group.id, archived=True)
    service.delete_group.assert_awaited_once_with(actor=ANY, group_id=group.id)


@pytest.mark.api
def test_type_mutation_routes_forward_group_and_optional_fields(
    defects_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = defects_client
    group = _group()
    defect_type = _type(group)
    service = SimpleNamespace(
        create_type=AsyncMock(return_value=defect_type),
        update_type=AsyncMock(return_value=defect_type),
        set_type_archived=AsyncMock(return_value=defect_type),
    )
    _configure_principal(app, mocker, service, Role.ADMINISTRATOR)

    created = client.post(
        "/defects/types",
        headers=_headers(),
        json={
            "group_id": str(group.id),
            "code": " VOLTAGE_LOW ",
            "name": " Low voltage ",
            "description": " Voltage is low. ",
            "possible_cause": "  ",
            "engineer_action": " Check cable ",
        },
    )
    updated = client.patch(
        f"/defects/types/{defect_type.id}",
        headers=_headers(),
        json={"possible_cause": " Loose cable "},
    )
    restored = client.put(
        f"/defects/types/{defect_type.id}/archived", headers=_headers(), json={"archived": False}
    )

    assert [response.status_code for response in (created, updated, restored)] == [
        status.HTTP_201_CREATED,
        status.HTTP_200_OK,
        status.HTTP_200_OK,
    ]
    service.create_type.assert_awaited_once_with(
        actor=ANY,
        group_id=group.id,
        code="VOLTAGE_LOW",
        name="Low voltage",
        description="Voltage is low.",
        possible_cause=None,
        engineer_action="Check cable",
    )
    service.update_type.assert_awaited_once_with(
        actor=ANY, defect_type_id=defect_type.id, updates={"possible_cause": "Loose cable"}
    )
    service.set_type_archived.assert_awaited_once_with(
        actor=ANY, defect_type_id=defect_type.id, archived=False
    )


@pytest.mark.api
def test_group_write_requires_defect_permission(
    defects_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = defects_client
    service = SimpleNamespace(create_group=AsyncMock())
    _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.post(
        "/defects/groups",
        headers=_headers(),
        json={"code": "POWER", "name": "Power supply"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    service.create_group.assert_not_awaited()
