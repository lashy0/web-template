from __future__ import annotations

import asyncio
import sys
from collections.abc import Generator
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
from app.core.config import Settings
from app.main import create_app
from app.modules.pak.models import PakDevice, PakDeviceKind
from app.modules.verification.exceptions import VerificationStepOutOfRangeError
from app.modules.verification.models import (
    VerificationSession,
    VerificationSessionStatus,
    VerificationStep,
    VerificationStepStatus,
)

_ALLOWED_ORIGIN = "https://admin.example"
_SESSION_COOKIE = "ory_kratos_session=opaque"


@pytest.fixture
def verification_client() -> Generator[tuple[FastAPI, TestClient]]:
    app = create_app(Settings.model_validate({"BACKEND_CORS_ORIGINS": [_ALLOWED_ORIGIN]}))
    backend_options: dict[str, object] = {}
    if sys.platform == "win32":
        backend_options["loop_factory"] = asyncio.SelectorEventLoop
    with TestClient(app, backend_options=backend_options) as client:
        yield app, client


def _pak() -> PakDevice:
    return PakDevice(
        id=uuid4(),
        code="PAK-OTK-01",
        kind=PakDeviceKind.OTK_LINE,
        oauth_client_id="pak-test",
        encrypted_access_key="ciphertext",
        is_active=True,
        archived_at=None,
    )


def _verification_session(pak: PakDevice) -> VerificationSession:
    now = datetime.now(UTC)
    return VerificationSession(
        id=uuid4(),
        kg_dev_eui="a1b2c3d4e5f60708",
        pak_id=pak.id,
        slot_no=1,
        firmware_version="1.2.3",
        total_steps=2,
        status=VerificationSessionStatus.RUNNING,
        started_at=now,
        last_activity_at=now,
        created_at=now,
        updated_at=now,
    )


def _step(verification_session: VerificationSession) -> VerificationStep:
    now = datetime.now(UTC)
    return VerificationStep(
        id=uuid4(),
        session_id=verification_session.id,
        pak_test_id=uuid4(),
        defect_group_id=uuid4(),
        step_no=1,
        test_name="voltage",
        test_label="Supply voltage",
        error_group_code="POWER",
        status=VerificationStepStatus.RUNNING,
        started_at=now,
        created_at=now,
        updated_at=now,
    )


def _configure_principal(app: FastAPI, mocker: MockerFixture, role: Role) -> None:
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
            id=uuid4(), role=role, name="Operator", identity_login="operator"
        )
    )


def _headers() -> dict[str, str]:
    return {"origin": _ALLOWED_ORIGIN, "cookie": _SESSION_COOKIE}


@pytest.mark.api
def test_list_sessions_serializes_items_and_forwards_filters(
    verification_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = verification_client
    pak = _pak()
    verification_session = _verification_session(pak)
    service = SimpleNamespace(list=AsyncMock(return_value=([verification_session], 1)))
    mocker.patch.object(app.state, "verification_management", service)
    _configure_principal(app, mocker, Role.ENGINEER)

    response = client.get(
        f"/verification/sessions?q=a1b2&pak_id={pak.id}&status=RUNNING&page=2&page_size=10"
        "&sort=created_at&order=asc",
        headers=_headers(),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"][0]["id"] == str(verification_session.id)
    service.list.assert_awaited_once_with(
        q="a1b2",
        pak_id=pak.id,
        status=VerificationSessionStatus.RUNNING,
        page=2,
        page_size=10,
        sort="created_at",
        order="asc",
    )


@pytest.mark.api
def test_list_sessions_requires_verification_read_permission(
    verification_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = verification_client
    service = SimpleNamespace(list=AsyncMock())
    mocker.patch.object(app.state, "verification_management", service)
    _configure_principal(app, mocker, Role.PACKER)

    response = client.get("/verification/sessions", headers=_headers())

    assert response.status_code == status.HTTP_403_FORBIDDEN
    service.list.assert_not_awaited()


@pytest.mark.api
def test_get_session_returns_ordered_step_detail(
    verification_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = verification_client
    verification_session = _verification_session(_pak())
    step = _step(verification_session)
    service = SimpleNamespace(get_detail=AsyncMock(return_value=(verification_session, [step])))
    mocker.patch.object(app.state, "verification_management", service)
    _configure_principal(app, mocker, Role.MANAGER)

    response = client.get(f"/verification/sessions/{verification_session.id}", headers=_headers())

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["steps"] == [
        {
            "id": str(step.id),
            "session_id": str(verification_session.id),
            "step_no": 1,
            "pak_test_id": str(step.pak_test_id),
            "defect_group_id": str(step.defect_group_id),
            "test_name": "voltage",
            "test_label": "Supply voltage",
            "status": "RUNNING",
            "measurement_value": None,
            "measurement_min_value": None,
            "measurement_max_value": None,
            "measurement_unit": None,
            "error_group_code": "POWER",
            "started_at": step.started_at.isoformat().replace("+00:00", "Z"),
            "completed_at": None,
            "created_at": step.created_at.isoformat().replace("+00:00", "Z"),
            "updated_at": step.updated_at.isoformat().replace("+00:00", "Z"),
        }
    ]
    service.get_detail.assert_awaited_once_with(verification_session.id)


@pytest.mark.api
def test_pak_lifecycle_routes_forward_normalized_payloads(
    verification_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = verification_client
    pak = _pak()
    verification_session = _verification_session(pak)
    step = _step(verification_session)
    service = SimpleNamespace(
        open_session=AsyncMock(return_value=verification_session),
        start_step=AsyncMock(return_value=step),
        complete_step=AsyncMock(return_value=step),
        complete_session=AsyncMock(return_value=verification_session),
    )
    mocker.patch.object(app.state, "verification_management", service)
    mocker.patch.object(
        app.state,
        "pak_management",
        SimpleNamespace(authorize_machine_access_token=AsyncMock(return_value=pak)),
    )
    token_headers = {"authorization": "Bearer machine-token"}

    opened = client.post(
        "/verification/sessions",
        headers=token_headers,
        json={
            "kg_dev_eui": "A1B2C3D4E5F60708",
            "slot_no": 1,
            "firmware_version": " 1.2.3 ",
            "total_steps": 2,
        },
    )
    started = client.post(
        f"/verification/sessions/{verification_session.id}/steps",
        headers=token_headers,
        json={
            "step_no": 1,
            "test_name": " voltage ",
            "test_label": " Supply voltage ",
            "error_group_code": " POWER ",
        },
    )
    completed_step = client.put(
        f"/verification/sessions/{verification_session.id}/steps/1",
        headers=token_headers,
        json={"status": "PASSED", "measurement_value": 12.0, "measurement_unit": " V "},
    )
    completed_session = client.post(
        f"/verification/sessions/{verification_session.id}/complete",
        headers=token_headers,
        json={"status": "PASSED"},
    )

    assert [response.status_code for response in (opened, started, completed_step, completed_session)] == [
        status.HTTP_201_CREATED,
        status.HTTP_201_CREATED,
        status.HTTP_200_OK,
        status.HTTP_200_OK,
    ]
    service.open_session.assert_awaited_once_with(
        pak=pak,
        kg_dev_eui="a1b2c3d4e5f60708",
        slot_no=1,
        firmware_version="1.2.3",
        total_steps=2,
    )
    service.start_step.assert_awaited_once_with(
        pak=pak,
        session_id=verification_session.id,
        step_no=1,
        test_name="voltage",
        test_label="Supply voltage",
        error_group_code="POWER",
    )
    service.complete_step.assert_awaited_once_with(
        pak=pak,
        session_id=verification_session.id,
        step_no=1,
        status=VerificationStepStatus.PASSED,
        measurement_value=12.0,
        measurement_min_value=None,
        measurement_max_value=None,
        measurement_unit="V",
    )
    service.complete_session.assert_awaited_once_with(
        pak=pak,
        session_id=verification_session.id,
        status=VerificationSessionStatus.PASSED,
    )


@pytest.mark.api
def test_pak_verification_requires_machine_bearer_token(
    verification_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = verification_client
    service = SimpleNamespace(open_session=AsyncMock())
    mocker.patch.object(app.state, "verification_management", service)

    response = client.post(
        "/verification/sessions",
        json={
            "kg_dev_eui": "a1b2c3d4e5f60708",
            "slot_no": 1,
            "firmware_version": "1.2.3",
            "total_steps": 2,
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "invalid_machine_access_token"
    service.open_session.assert_not_awaited()


@pytest.mark.api
def test_verification_errors_map_to_api_response(
    verification_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = verification_client
    pak = _pak()
    service = SimpleNamespace(complete_step=AsyncMock(side_effect=VerificationStepOutOfRangeError))
    mocker.patch.object(app.state, "verification_management", service)
    mocker.patch.object(
        app.state,
        "pak_management",
        SimpleNamespace(authorize_machine_access_token=AsyncMock(return_value=pak)),
    )

    response = client.put(
        f"/verification/sessions/{uuid4()}/steps/3",
        headers={"authorization": "Bearer machine-token"},
        json={"status": "PASSED"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "verification_step_out_of_range"
