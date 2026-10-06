from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from ory_kratos_client.exceptions import ApiException

from app.config.kratos import KratosSettings
from app.lib.kratos.session import KratosSessionVerifier

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.unit,
    pytest.mark.auth,
]

_COOKIE = "ory_kratos_session=session-value"


def _verifier(*, expires_in: timedelta) -> tuple[KratosSessionVerifier, MagicMock]:
    """Return a verifier whose Kratos session expires in ``expires_in`` and its ``extend_session`` mock."""
    verifier = KratosSessionVerifier(
        KratosSettings.model_validate({"BACKEND_KRATOS_SESSION_EXTEND_WITHIN_MINUTES": 60})
    )
    frontend = MagicMock()
    frontend.to_session.return_value = MagicMock(
        id=uuid4(),
        active=True,
        expires_at=datetime.now(UTC) + expires_in,
        identity=MagicMock(id=str(uuid4()), traits={"login": "operator"}, state="active", metadata_admin=None),
    )
    identities = MagicMock()
    verifier._api = frontend
    verifier._identities = identities

    return verifier, identities.extend_session


async def test_session_far_from_expiry_is_not_extended() -> None:
    verifier, extend_session = _verifier(expires_in=timedelta(hours=2))

    identity = await verifier.verify_session(cookie_header=_COOKIE)

    assert identity.login == "operator"
    extend_session.assert_not_called()


async def test_session_close_to_expiry_is_extended() -> None:
    verifier, extend_session = _verifier(expires_in=timedelta(minutes=30))

    await verifier.verify_session(cookie_header=_COOKIE)

    extend_session.assert_called_once()


async def test_failed_extension_keeps_request_authenticated() -> None:
    verifier, extend_session = _verifier(expires_in=timedelta(minutes=30))
    extend_session.side_effect = ApiException(status=404)

    identity = await verifier.verify_session(cookie_header=_COOKIE)

    assert identity.login == "operator"
