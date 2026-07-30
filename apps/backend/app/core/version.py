import tomllib
from pathlib import Path
from typing import Any

PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


def read_project_version(pyproject_path: Path = PYPROJECT_PATH) -> str:
    with pyproject_path.open("rb") as pyproject_file:
        pyproject: dict[str, Any] = tomllib.load(pyproject_file)

    version = pyproject.get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise RuntimeError(f"Project version is missing in {pyproject_path}")

    return version


APP_VERSION = read_project_version()
