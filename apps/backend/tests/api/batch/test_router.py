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
from app.modules.batch.models import Batch, BatchReceipt, BatchShipment, BatchStatus

_ALLOWED_ORIGIN = "https://admin.example"
_SESSION_COOKIE = "ory_kratos_session=opaque"


@pytest.fixture
def batch_client() -> Generator[tuple[FastAPI, TestClient]]:
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


def _batch(*, batch_id: UUID | None = None) -> Batch:
    now = datetime.now(UTC)
    return Batch(
        id=batch_id or uuid4(),
        name="August production",
        description="Initial run",
        dev_eui_prefix="a1b2c3d4e5",
        planned_qty=100,
        day_plan_qty=20,
        status=BatchStatus.IN_PRODUCTION,
        created_by_user_id=uuid4(),
        created_at=now,
        updated_at=now,
        completed_at=None,
        archived_at=None,
    )


def _receipt(*, batch_id: UUID) -> BatchReceipt:
    now = datetime.now(UTC)
    return BatchReceipt(
        id=uuid4(),
        batch_id=batch_id,
        quantity=10,
        comment="accepted",
        created_by_user_id=uuid4(),
        created_at=now,
        updated_at=now,
        voided_at=None,
        void_reason=None,
    )


def _shipment(*, batch_id: UUID) -> BatchShipment:
    now = datetime.now(UTC)
    return BatchShipment(
        id=uuid4(),
        batch_id=batch_id,
        comment="outbound",
        created_by_user_id=uuid4(),
        created_at=now,
        updated_at=now,
        completed_at=None,
        voided_at=None,
        void_reason=None,
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
    mocker.patch.object(app.state, "batch_management", service)
    return user_id


def _headers() -> dict[str, str]:
    return {"origin": _ALLOWED_ORIGIN, "cookie": _SESSION_COOKIE}


@pytest.mark.api
def test_list_batches_serializes_items_and_forwards_filters(
    batch_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = batch_client
    batch = _batch()
    service = SimpleNamespace(list=AsyncMock(return_value=([batch], 1)))
    _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.get(
        "/batches/?q=August&status=IN_PRODUCTION&archived=false&page=2&page_size=10"
        "&sort=name&order=asc",
        headers=_headers(),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"][0]["name"] == batch.name
    service.list.assert_awaited_once_with(
        q="August",
        status=BatchStatus.IN_PRODUCTION,
        archived=False,
        page=2,
        page_size=10,
        sort="name",
        order="asc",
    )


@pytest.mark.api
def test_create_batch_normalizes_payload_and_forwards_actor(
    batch_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = batch_client
    batch = _batch()
    service = SimpleNamespace(create=AsyncMock(return_value=batch))
    actor_id = _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.post(
        "/batches",
        headers=_headers(),
        json={
            "name": "  August production  ",
            "description": "Initial run",
            "dev_eui_prefix": "A1B2C3D4E5",
            "planned_qty": 100,
            "day_plan_qty": 20,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    service.create.assert_awaited_once_with(
        actor=ANY,
        name="August production",
        description="Initial run",
        dev_eui_prefix="a1b2c3d4e5",
        planned_qty=100,
        day_plan_qty=20,
    )
    assert service.create.await_args.kwargs["actor"].user_id == actor_id


@pytest.mark.api
def test_missing_batch_returns_not_found(
    batch_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = batch_client
    service = SimpleNamespace(get=AsyncMock(return_value=None))
    _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.get(f"/batches/{uuid4()}", headers=_headers())

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "batch_not_found"


@pytest.mark.api
def test_receipt_mutations_are_forwarded_to_service(
    batch_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = batch_client
    batch = _batch()
    receipt = _receipt(batch_id=batch.id)
    service = SimpleNamespace(
        create_receipt=AsyncMock(return_value=receipt),
        update_receipt=AsyncMock(return_value=receipt),
        void_receipt=AsyncMock(return_value=receipt),
    )
    actor_id = _configure_principal(app, mocker, service, Role.MANAGER)

    create_response = client.post(
        f"/batches/{batch.id}/receipts",
        headers=_headers(),
        json={"quantity": 10, "comment": "accepted"},
    )
    update_response = client.patch(
        f"/batches/{batch.id}/receipts/{receipt.id}",
        headers=_headers(),
        json={"quantity": 12},
    )
    void_response = client.post(
        f"/batches/{batch.id}/receipts/{receipt.id}/void",
        headers=_headers(),
        json={"reason": "  duplicate  "},
    )

    assert [
        response.status_code for response in (create_response, update_response, void_response)
    ] == [
        status.HTTP_201_CREATED,
        status.HTTP_200_OK,
        status.HTTP_200_OK,
    ]
    service.create_receipt.assert_awaited_once_with(
        actor=ANY,
        batch_id=batch.id,
        quantity=10,
        comment="accepted",
    )
    service.update_receipt.assert_awaited_once_with(
        actor=ANY,
        batch_id=batch.id,
        receipt_id=receipt.id,
        updates={"quantity": 12},
    )
    service.void_receipt.assert_awaited_once_with(
        actor=ANY,
        batch_id=batch.id,
        receipt_id=receipt.id,
        reason="duplicate",
    )
    assert service.create_receipt.await_args.kwargs["actor"].user_id == actor_id


@pytest.mark.api
def test_shipment_routes_include_item_quantity_and_normalize_dev_eui(
    batch_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = batch_client
    batch = _batch()
    shipment = _shipment(batch_id=batch.id)
    service = SimpleNamespace(
        create_shipment=AsyncMock(return_value=shipment),
        add_shipment_item=AsyncMock(
            return_value=SimpleNamespace(
                shipment_id=shipment.id,
                kg_dev_eui="a1b2c3d4e5f60708",
                created_at=datetime.now(UTC),
            )
        ),
        count_shipment_items=AsyncMock(return_value=1),
    )
    _configure_principal(app, mocker, service, Role.MANAGER)

    shipment_response = client.post(
        f"/batches/{batch.id}/shipments",
        headers=_headers(),
        json={"comment": "outbound"},
    )
    item_response = client.post(
        f"/batches/{batch.id}/shipments/{shipment.id}/items",
        headers=_headers(),
        json={"dev_eui": "A1B2C3D4E5F60708"},
    )

    assert shipment_response.status_code == status.HTTP_201_CREATED
    assert shipment_response.json()["quantity"] == 1
    assert item_response.status_code == status.HTTP_201_CREATED
    service.add_shipment_item.assert_awaited_once_with(
        actor=ANY,
        batch_id=batch.id,
        shipment_id=shipment.id,
        dev_eui="a1b2c3d4e5f60708",
    )


@pytest.mark.api
def test_batch_routes_require_their_permission(
    batch_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = batch_client
    service = SimpleNamespace(list=AsyncMock())
    _configure_principal(app, mocker, service, Role.ENGINEER)

    response = client.get("/batches/", headers=_headers())

    assert response.status_code == status.HTTP_403_FORBIDDEN
    service.list.assert_not_awaited()
