import pytest

from app.config.settings import get_settings

pytestmark = pytest.mark.anyio


def test_app_slug() -> None:
    """Test app name conversion to slug."""
    settings = get_settings()
    settings.app.name = "My Application!"
    assert settings.app.slug == "my-application"
