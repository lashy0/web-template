# /// script
# requires-python = ">=3.13,<4"
# dependencies = []
# ///

import os
import shutil
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPOSITORY_ROOT / "apps/backend"
COMPOSE_FILES = (
    REPOSITORY_ROOT / "docker-compose.yaml",
    REPOSITORY_ROOT / "docker-compose.prod.yaml",
)


def read_backend_version(uv: str) -> str:
    result = subprocess.run(
        [
            uv,
            "version",
            "--project",
            str(BACKEND_ROOT),
            "--short",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    version = result.stdout.strip()
    if not version:
        raise RuntimeError(
            f"Project version is missing in {BACKEND_ROOT / 'pyproject.toml'}"
        )

    return version


def main() -> None:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is not installed or is not available on PATH")

    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("Docker CLI is not installed or is not available on PATH")

    version = read_backend_version(uv)
    environment = os.environ.copy()
    environment["TAG"] = version

    command = [docker, "compose"]
    for compose_file in COMPOSE_FILES:
        command.extend(("-f", str(compose_file)))
    command.extend(("up", "-d", "--build"))

    print(f"Deploying web-app-backend:{version}", flush=True)

    subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
    )


if __name__ == "__main__":
    main()
