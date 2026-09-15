import pytest

from app.main import create_app


@pytest.mark.api
def test_verification_openapi_paths_and_methods_are_unchanged() -> None:
    paths = create_app().openapi()["paths"]
    assert {path for path in paths if path.startswith("/verification")} == {
        "/verification/sessions",
        "/verification/sessions/{session_id}",
        "/verification/sessions/{session_id}/steps",
        "/verification/sessions/{session_id}/steps/{step_no}",
        "/verification/sessions/{session_id}/complete",
    }
    assert set(paths["/verification/sessions"]) == {"get", "post"}
    assert set(paths["/verification/sessions/{session_id}/steps"]) == {"post"}
    assert set(paths["/verification/sessions/{session_id}/steps/{step_no}"]) == {"put"}
    assert set(paths["/verification/sessions/{session_id}/complete"]) == {"post"}
