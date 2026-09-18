from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest

from app.lib.kratos.client import _to_identity
from app.lib.kratos.exceptions import KratosUnavailableError


@pytest.mark.unit
def test_to_identity_converts_valid_kratos_sdk_response() -> None:
    identity_id = UUID("01995000-0000-7000-8000-000000000101")
    sdk_identity = SimpleNamespace(
        id=str(identity_id),
        traits={"login": "operator", "ignored": "value"},
        state="active",
        metadata_admin={"provisioning": {"owner": "backend"}},
    )

    identity = _to_identity(sdk_identity)  # type: ignore[arg-type]

    assert identity.id == identity_id
    assert identity.login == "operator"
    assert identity.is_active is True
    assert identity.metadata == {"provisioning": {"owner": "backend"}}


@pytest.mark.unit
@pytest.mark.parametrize(
    "traits",
    [None, [], {}, {"login": 123}],
)
def test_to_identity_rejects_invalid_login_traits(traits: object) -> None:
    sdk_identity = SimpleNamespace(
        id="01995000-0000-7000-8000-000000000101",
        traits=traits,
        state="inactive",
        metadata_admin=None,
    )

    with pytest.raises(KratosUnavailableError):
        _to_identity(sdk_identity)  # type: ignore[arg-type]


@pytest.mark.unit
@pytest.mark.parametrize("metadata", [[], "invalid"])
def test_to_identity_rejects_invalid_admin_metadata(metadata: object) -> None:
    sdk_identity = SimpleNamespace(
        id="01995000-0000-7000-8000-000000000101",
        traits={"login": "operator"},
        state="inactive",
        metadata_admin=metadata,
    )

    with pytest.raises(KratosUnavailableError, match="admin metadata"):
        _to_identity(sdk_identity)  # type: ignore[arg-type]
