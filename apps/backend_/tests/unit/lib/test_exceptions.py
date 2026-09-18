import pytest

from app.lib.exceptions import ApplicationError

pytestmark = pytest.mark.anyio


def test_application_error_init() -> None:
    exc = ApplicationError("msg", detail="detailed info")
    assert exc.detail == "detailed info"
    assert "msg" in str(exc)
    assert "detailed info" in str(exc)

    exc2 = ApplicationError("msg")
    assert exc2.detail == "msg"

    assert "ApplicationError" in repr(exc)
