import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth_deps import get_current_principal
from app.auth.principal import CurrentPrincipal
from app.auth.roles import Role
from app.main import create_app
from app.modules.batch.services import BatchManagementService
from app.modules.production_order.exceptions import (
    ProductionOrderArchivedError,
    ProductionOrderCannotBeDeletedError,
    ProductionOrderNotFoundError,
)
from app.modules.production_order.models import ProductionOrder
from tools.export_openapi import export_openapi

pytestmark = pytest.mark.api


@pytest.fixture
def api():
    app = create_app()
    actor = CurrentPrincipal(
        user_id=uuid4(), identity_id=uuid4(), session_id=uuid4(), role=Role.MANAGER
    )
    app.dependency_overrides[get_current_principal] = lambda: actor
    service = MagicMock()
    app.state.production_order_management = service
    now = datetime.now(UTC)
    response = ProductionOrder(
        id=uuid4(),
        name="Order",
        description=None,
        created_at=now,
        updated_at=now,
        archived_at=None,
    )
    service.get = AsyncMock(return_value=response)
    service.list = AsyncMock(return_value=([(response, 0, 0)], 1))
    service.get_totals = AsyncMock(return_value=(0, 0))
    for name in ("create", "update", "set_archived", "delete"):
        setattr(service, name, AsyncMock(return_value=response))
    client = TestClient(app)
    prefix = app.state.settings.API_PREFIX
    return app, client, prefix, actor, service, response


def test_list_filters_and_response(api):
    _, client, prefix, _, service, response = api
    result = client.get(
        f"{prefix}/production-orders/",
        params={
            "q": "Order",
            "archived": True,
            "page": 2,
            "page_size": 10,
            "sort": "total_planned_qty",
            "order": "asc",
        },
    )
    assert result.status_code == 200
    assert result.json()["items"][0]["id"] == str(response.id)
    service.list.assert_awaited_once_with(
        q="Order", archived=True, page=2, page_size=10, sort="total_planned_qty", order="asc"
    )


def test_crud_and_archive_forward_validated_payload(api):
    _, client, prefix, actor, service, response = api
    url = f"{prefix}/production-orders"
    assert client.post(url, json={"name": "  Order  "}).status_code == 201
    service.create.assert_awaited_once_with(actor=actor, name="Order", description=None)
    assert client.get(f"{url}/{response.id}").status_code == 200
    assert client.patch(f"{url}/{response.id}", json={"description": None}).status_code == 200
    service.update.assert_awaited_once_with(
        order_id=response.id, actor=actor, updates={"description": None}
    )
    assert client.put(f"{url}/{response.id}/archived", json={"archived": True}).status_code == 200
    service.set_archived.assert_awaited_once_with(order_id=response.id, actor=actor, archived=True)
    assert client.delete(f"{url}/{response.id}").status_code == 204


@pytest.mark.parametrize(
    "params", [{"page": 0}, {"page_size": 101}, {"sort": "unknown"}, {"order": "bad"}]
)
def test_invalid_list_parameters(api, params):
    _, client, prefix, _, service, _ = api
    assert client.get(f"{prefix}/production-orders/", params=params).status_code == 422
    service.list.assert_not_awaited()


@pytest.mark.parametrize("role", [Role.ENGINEER, Role.OPERATOR, Role.PACKER])
def test_other_roles_cannot_access_orders(api, role):
    app, client, prefix, _, service, response = api
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        user_id=uuid4(), identity_id=uuid4(), session_id=uuid4(), role=role
    )
    url = f"{prefix}/production-orders"
    for method, path, body in [
        ("GET", url + "/", None),
        ("POST", url, {"name": "Order"}),
        ("PATCH", f"{url}/{response.id}", {"name": "Changed"}),
        ("PUT", f"{url}/{response.id}/archived", {"archived": True}),
        ("DELETE", f"{url}/{response.id}", None),
        ("PUT", f"{prefix}/batches/{uuid4()}/production-order", {"production_order_id": None}),
    ]:
        assert client.request(method, path, json=body).status_code == 403
    service.list.assert_not_awaited()


def test_missing_and_used_order_errors(api):
    _, client, prefix, _, service, response = api
    service.get.return_value = None
    assert client.get(f"{prefix}/production-orders/{response.id}").status_code == 404
    service.delete.side_effect = ProductionOrderCannotBeDeletedError
    result = client.delete(f"{prefix}/production-orders/{response.id}")
    assert result.status_code == 409
    assert "production_order_cannot_be_deleted" in result.text


@pytest.mark.parametrize(
    "error,expected", [(ProductionOrderNotFoundError, 404), (ProductionOrderArchivedError, 409)]
)
def test_assignment_errors_and_explicit_null(api, error, expected):
    app, client, prefix, actor, _, _ = api
    service = MagicMock()
    service.assign_production_order = AsyncMock(side_effect=error)
    app.state.batch_management = service
    batch_id = uuid4()
    url = f"{prefix}/batches/{batch_id}/production-order"
    assert client.put(url, json={}).status_code == 422
    assert client.put(url, json={"production_order_id": None}).status_code == expected
    service.assign_production_order.assert_awaited_once_with(
        actor=actor, batch_id=batch_id, production_order_id=None
    )


def test_conflicting_batch_filters(api):
    app, client, prefix, _, _, _ = api
    session_factory = MagicMock()
    app.state.batch_management = BatchManagementService(session_factory)
    result = client.get(
        f"{prefix}/batches/",
        params={"production_order_id": str(uuid4()), "without_production_order": True},
    )
    assert result.status_code == 422
    assert result.json()["code"] == "batch_invalid_filters"
    session_factory.assert_not_called()


def test_order_contract_is_exported_only_for_web(tmp_path):
    app: FastAPI = create_app()
    for audience in ("web", "machine"):
        output = tmp_path / f"{audience}.json"
        export_openapi(app, output, audience)
        schema = json.loads(output.read_text())
        assert any("/production-orders" in path for path in schema["paths"]) == (audience == "web")
