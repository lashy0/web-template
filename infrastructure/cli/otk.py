"""Run backend commands from the host in the running API container.

``otk users create`` runs ``python -m app.otk users create`` inside the container,
where the backend reaches PostgreSQL and the Kratos Admin API; neither is
published on the host. Arguments are passed through unchanged; the backend's
``app.otk`` decides which commands operators get.
"""

import os
import subprocess
import sys

from cli.compose import DeploymentError, find_tool, run_command
from cli.output import console

BACKEND_PROJECT = "otk-app-backend"
API_SERVICE = "api"


def find_api_container(docker: str) -> str:
    containers = run_command(
        [
            docker,
            "ps",
            "--quiet",
            "--filter",
            f"label=com.docker.compose.project={BACKEND_PROJECT}",
            "--filter",
            f"label=com.docker.compose.service={API_SERVICE}",
        ],
        capture_output=True,
    ).stdout.split()

    if not containers:
        raise DeploymentError(
            "The backend API container is not running. Start it with: infra backend up <env>"
        )

    return containers[0]


def backend_command(docker: str, arguments: list[str], *, tty: bool = False) -> list[str]:
    """Return the ``docker exec`` command running ``python -m app.otk`` in the API container."""
    return [
        docker,
        "exec",
        "--interactive",
        *(["--tty"] if tty else []),
        find_api_container(docker),
        "python",
        "-m",
        "app.otk",
        *arguments,
    ]


def run(arguments: list[str]) -> int:
    docker = find_tool("docker")
    # Prompts such as the password need an interactive terminal when there is one.
    tty = sys.stdin.isatty() and sys.stdout.isatty()
    command = backend_command(docker, arguments, tty=tty)
    # Docker otherwise advertises its own tools after a failed command.
    environment = {**os.environ, "DOCKER_CLI_HINTS": "false"}

    return subprocess.run(command, check=False, env=environment).returncode


def main() -> None:
    try:
        code = run(sys.argv[1:] or ["--help"])
    except DeploymentError as error:
        console.print(f"Error: {error}", style="bold red")
        raise SystemExit(1) from None
    except subprocess.CalledProcessError as error:
        console.print(
            error.stderr.rstrip()
            if error.stderr
            else f"Error: command failed with exit code {error.returncode}.",
            style="red",
            soft_wrap=True,
        )
        raise SystemExit(error.returncode) from None

    raise SystemExit(code)


if __name__ == "__main__":
    main()
