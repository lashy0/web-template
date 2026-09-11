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
from app.modules.batch import exceptions as batch_errors
from app.modules.batch.models import (
    ActivationType,
    Batch,
    BatchKeyGenerationStatus,
    BatchLoRaWanConfig,
    BatchReceipt,
    BatchShipment,
    BatchStatus,
    LoRaWanVersion,
)
from app.modules.kg.models import KgDevEuiPrefix, KgVersion

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


def _batch(*, batch_id: UUID | None = None, version: KgVersion | None = None) -> Batch:
    now = datetime.now(UTC)
    prefix = KgDevEuiPrefix(
        prefix="a1b2c3d4e5",
        short_code="kg",
        name="Основной",
        created_at=now,
    )
    return Batch(
        id=batch_id or uuid4(),
        name="August production",
        description="Initial run",
        dev_eui_prefix="a1b2c3d4e5",
        planned_qty=100,
        day_plan_qty=20,
        status=BatchStatus.IN_PRODUCTION,
        key_generation_status=BatchKeyGenerationStatus.PENDING,
        created_by_user_id=uuid4(),
        created_at=now,
        updated_at=now,
        completed_at=None,
        archived_at=None,
        kg_dev_eui_prefix=prefix,
        kg_version=version,
    )


def _version(*, archived: bool = False) -> KgVersion:
    now = datetime.now(UTC)
    return KgVersion(
        id=uuid4(),
        code="3.0",
        name="Слон 3.0",
        description=None,
        created_at=now,
        updated_at=now,
        archived_at=now if archived else None,
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
    if not hasattr(service, "deletion_availability"):
        service.deletion_availability = AsyncMock(
            side_effect=lambda batches: {batch.id: True for batch in batches}
        )

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
    assert response.json()["items"][0]["dev_eui_prefix"] == {
        "prefix": "a1b2c3d4e5",
        "short_code": "kg",
        "name": "Основной",
    }
    assert response.json()["items"][0]["kg_version"] is None
    assert response.json()["items"][0]["can_delete"] is True
    service.list.assert_awaited_once_with(
        q="August",
        status=BatchStatus.IN_PRODUCTION,
        archived=False,
        page=2,
        page_size=10,
        sort="name",
        order="asc",
        production_order_id=None,
        without_production_order=False,
    )


@pytest.mark.api
def test_preview_dev_eui_range_returns_current_bounds(
    batch_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = batch_client
    service = SimpleNamespace(
        preview_dev_eui_range=AsyncMock(return_value=("a1b2c3d4e5000001", "a1b2c3d4e5000064"))
    )
    _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.get(
        "/batches/dev-eui-range-preview?dev_eui_prefix=A1B2C3D4E5&planned_qty=100",
        headers=_headers(),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "first_dev_eui": "a1b2c3d4e5000001",
        "last_dev_eui": "a1b2c3d4e5000064",
    }
    service.preview_dev_eui_range.assert_awaited_once_with(
        dev_eui_prefix="a1b2c3d4e5",
        planned_qty=100,
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
            "lorawan_config": {"activation_type": "otaa", "lorawan_version": "1.1"},
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["key_generation_status"] == "PENDING"
    service.create.assert_awaited_once_with(
        actor=ANY,
        name="August production",
        description="Initial run",
        dev_eui_prefix="a1b2c3d4e5",
        planned_qty=100,
        day_plan_qty=20,
        activation_type=ActivationType.OTAA,
        lorawan_version=LoRaWanVersion.V1_1,
        production_order_id=None,
    )
    assert service.create.await_args.kwargs["actor"].user_id == actor_id


@pytest.mark.api
def test_batch_response_includes_lorawan_config(batch_client, mocker) -> None:
    app, client = batch_client
    batch = _batch()
    batch.lorawan_config = BatchLoRaWanConfig(
        batch_id=batch.id,
        activation_type=ActivationType.OTAA,
        lorawan_version=LoRaWanVersion.V1_1,
        join_eui="0123456789abcdef",
    )
    service = SimpleNamespace(get=AsyncMock(return_value=batch))
    _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.get(f"/batches/{batch.id}", headers=_headers())

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["lorawan_config"] == {
        "activation_type": "otaa",
        "lorawan_version": "1.1",
        "join_eui": "0123456789abcdef",
    }


@pytest.mark.api
def test_batch_response_includes_archived_version_details(
    batch_client: tuple[FastAPI, TestClient],
    mocker: MockerFixture,
) -> None:
    app, client = batch_client
    version = _version(archived=True)
    batch = _batch(version=version)
    service = SimpleNamespace(get=AsyncMock(return_value=batch))
    _configure_principal(app, mocker, service, Role.MANAGER)

    response = client.get(f"/batches/{batch.id}", headers=_headers())

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["kg_version"] == {
        "id": str(version.id),
        "code": "3.0",
        "name": "Слон 3.0",
    }
    assert "kg_version_id" not in response.json()


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


@pytest.mark.api
@pytest.mark.parametrize(
    "error,expected",
    [
        (batch_errors.BatchAlreadyCompletedError, 409),
        (batch_errors.BatchArchivedError, 409),
        (batch_errors.BatchShipmentKgAlreadyAssignedError, 409),
        (batch_errors.BatchShipmentKgStateConflictError, 409),
        (batch_errors.BatchConflictError, 409),
        (batch_errors.BatchShipmentKgNotFoundError, 404),
        (batch_errors.BatchShipmentNotFoundError, 404),
        (batch_errors.BatchReceiptNotFoundError, 404),
        (batch_errors.BatchShipmentItemNotFoundError, 404),
    ],
)
def test_domain_failures_have_stable_error_envelope(batch_client, mocker, error, expected):
    app, client = batch_client
    service = SimpleNamespace(complete=AsyncMock(side_effect=error))
    _configure_principal(app, mocker, service, Role.MANAGER)
    response = client.post(f"/batches/{uuid4()}/complete", headers=_headers())
    assert response.status_code == expected
    assert response.json()["code"] == error.code
    assert set(response.json()) == {"code", "message", "request_id"}


@pytest.mark.api
@pytest.mark.parametrize("empty", [False, True])
def test_shipment_list_uses_bulk_quantities(batch_client, mocker, empty):
    app, client = batch_client
    batch = _batch()
    first, second = _shipment(batch_id=batch.id), _shipment(batch_id=batch.id)
    service = SimpleNamespace(
        list_shipments=AsyncMock(return_value=[] if empty else [first, second]),
        count_shipment_quantities=AsyncMock(return_value={first.id: 3}),
        count_shipment_items=AsyncMock(side_effect=AssertionError("per-item query")),
    )
    _configure_principal(app, mocker, service, Role.MANAGER)
    response = client.get(f"/batches/{batch.id}/shipments", headers=_headers())
    assert response.status_code == 200
    assert [item["quantity"] for item in response.json()["items"]] == ([] if empty else [3, 0])
    service.count_shipment_items.assert_not_awaited()
    if empty:
        service.count_shipment_quantities.assert_not_awaited()
    else:
        service.count_shipment_quantities.assert_awaited_once_with(batch.id)


@pytest.mark.api
@pytest.mark.parametrize("has_author", [False, True])
def test_batch_response_author_is_a_safe_summary(batch_client, mocker, has_author):
    from app.modules.users.models import User

    app, client = batch_client
    batch = _batch()
    author = User(id=uuid4(), name="Author", identity_login="private-login") if has_author else None
    batch.created_by_user = author
    batch.created_by_user_id = author.id if author else None
    service = SimpleNamespace(get=AsyncMock(return_value=batch))
    _configure_principal(app, mocker, service, Role.MANAGER)
    response = client.get(f"/batches/{batch.id}", headers=_headers())
    assert response.status_code == 200
    assert response.json()["created_by_user"] == (
        {"id": str(author.id), "name": "Author"} if author else None
    )
