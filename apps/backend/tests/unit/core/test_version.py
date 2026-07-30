from pathlib import Path

import pytest

from app.core.version import APP_VERSION, PYPROJECT_PATH, read_project_version


@pytest.mark.unit
def test_app_version_matches_pyproject() -> None:
    assert APP_VERSION == read_project_version(PYPROJECT_PATH)


@pytest.mark.unit
def test_read_project_version_rejects_missing_version(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text('[project]\nname = "backend"\n', encoding="utf-8")

    with pytest.raises(RuntimeError, match="Project version is missing"):
        read_project_version(pyproject_path)
