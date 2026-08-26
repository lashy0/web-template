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
from app.auth.exceptions import IdentityProviderUnavailableError
from app.auth.roles import Role


class _SessionFactory:
    def __call__(self) -> _SessionFactory:
        return self

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *args: object) -> None:
        return None


def _authenticated_session(*, active: bool = True) -> AuthSession:
    return AuthSession(
        id=uuid4(),
        identity=Identity(id=uuid4(), login="alice", active=active),
        expires_at=datetime.now(UTC),
    )


def _configure_authenticated_request(
    app: FastAPI,
    mocker: MockerFixture,
    *,
    role: Role,
) -> tuple[AuthSession, AsyncMock]:
    session = _authenticated_session()
    verifier = SimpleNamespace(verify_session=AsyncMock(return_value=session))
    service = SimpleNamespace(list=AsyncMock(return_value=([], 0)))
    repository = mocker.patch("app.api.auth_deps.UserRepository")
    repository.return_value.get_by_identity_id = AsyncMock(
        return_value=SimpleNamespace(
            id=uuid4(),
            role=role,
            name="Alice",
            identity_login="alice",
        )
    )
    mocker.patch.object(app.state, "session_verifier", verifier)
    mocker.patch.object(app.state, "database", SimpleNamespace(session_factory=_SessionFactory()))
    mocker.patch.object(app.state, "user_management", service)
    return session, service.list


@pytest.mark.api
def test_protected_route_maps_missing_cookie_to_invalid_session(
    client: TestClient,
    api_prefix: str,
) -> None:
    response = client.get(f"{api_prefix}/users")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "invalid_session"


@pytest.mark.api
def test_protected_route_maps_kratos_unavailability_to_service_unavailable(
    app: FastAPI,
    client: TestClient,
    api_prefix: str,
    mocker: MockerFixture,
) -> None:
    verifier = SimpleNamespace(
        verify_session=AsyncMock(side_effect=IdentityProviderUnavailableError)
    )
    mocker.patch.object(app.state, "session_verifier", verifier)

    response = client.get(f"{api_prefix}/users", headers={"cookie": "ory_kratos_session=opaque"})

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["code"] == "identity_provider_unavailable"


@pytest.mark.api
def test_administrator_can_access_a_protected_user_route(
    app: FastAPI,
    client: TestClient,
    api_prefix: str,
    mocker: MockerFixture,
) -> None:
    session, list_users = _configure_authenticated_request(app, mocker, role=Role.ADMINISTRATOR)

    response = client.get(f"{api_prefix}/users", headers={"cookie": "ory_kratos_session=opaque"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 25}
    list_users.assert_awaited_once_with(
        q=None,
        role=None,
        auth_state=None,
        archived=False,
        page=1,
        page_size=25,
        sort="name",
        order="asc",
    )
    assert session.identity.active is True


@pytest.mark.api
def test_user_route_rejects_authenticated_role_without_permission(
    app: FastAPI,
    client: TestClient,
    api_prefix: str,
    mocker: MockerFixture,
) -> None:
    _, list_users = _configure_authenticated_request(app, mocker, role=Role.MANAGER)

    response = client.get(f"{api_prefix}/users", headers={"cookie": "ory_kratos_session=opaque"})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "forbidden"
    list_users.assert_not_awaited()


@pytest.mark.api
def test_user_creation_requires_json_content_type(client: TestClient, api_prefix: str) -> None:
    response = client.post(f"{api_prefix}/users")

    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert response.json()["code"] == "json_required"


@pytest.mark.api
def test_user_creation_rejects_untrusted_origin(client: TestClient, api_prefix: str) -> None:
    response = client.post(
        f"{api_prefix}/users",
        json={},
        headers={"origin": "https://untrusted.example"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "invalid_origin"
