import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from cli.output import ServiceStatus, console, current_step

INFRASTRUCTURE_ROOT = Path(__file__).resolve().parent.parent
REPOSITORY_ROOT = INFRASTRUCTURE_ROOT.parent
ROOT_ENV_FILE = REPOSITORY_ROOT / ".env"

DATABASE_NETWORK = "otk-app-database"
IDENTITY_NETWORK = "otk-app-identity"
TRAEFIK_NETWORK = "traefik-public"


class Environment(StrEnum):
    DEV = "dev"
    PROD = "prod"


EnvironmentArgument = Annotated[
    Environment,
    typer.Argument(help="Configuration: dev or prod.", show_default=False),
]
HealthTimeoutOption = Annotated[
    int,
    typer.Option(min=1, help="Seconds to wait until the services are healthy."),
]
ServicesArgument = Annotated[
    list[str] | None,
    typer.Argument(help="Services to show. All by default.", show_default=False),
]

ENV_ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?(?P<key>[A-Za-z_]\w*)\s*=(?P<value>.*)$")
_EXIT_CODE = re.compile(r"Exited \((?P<code>-?\d+)\)")
_HEALTH = re.compile(r"\((?:health: )?(?P<health>healthy|unhealthy|starting)\)")


class DeploymentError(RuntimeError):
    """An expected operational error that can be shown without a traceback."""


def parse_env(text: str) -> dict[str, str]:
    return {
        match["key"]: match["value"].strip().strip("'\"")
        for line in text.splitlines()
        if (match := ENV_ASSIGNMENT.match(line))
    }


def read_env_file(path: Path) -> dict[str, str]:
    return parse_env(path.read_text(encoding="utf-8")) if path.is_file() else {}


@dataclass(frozen=True, slots=True)
class ComposeProject:
    name: str
    title: str
    command_name: str
    """The ``infra`` subcommand that manages the project."""
    root: Path
    env_files: tuple[Path, ...] = (ROOT_ENV_FILE,)
    jobs: tuple[str, ...] = ()
    """One-shot services, such as migrations, that exit after their work."""

    def prepare(
        self,
        docker: str,
        environment: Environment,
        *,
        process_environment: dict[str, str] | None = None,
    ) -> list[str]:
        for env_file in self.env_files:
            if not env_file.is_file():
                raise DeploymentError(
                    f"Environment file does not exist: {env_file}. Create it with 'infra init'."
                )

        compose_files = (
            self.root / "docker-compose.yaml",
            self.root / f"docker-compose.{environment.value}.yaml",
        )
        command = [docker, "compose"]

        for env_file in self.env_files:
            command.extend(("--env-file", str(env_file)))

        for compose_file in compose_files:
            command.extend(("--file", str(compose_file)))

        result = run_command(
            [*command, "config", "--quiet"],
            check=False,
            capture_output=True,
            process_environment=process_environment,
        )

        if result.returncode != 0:
            raise DeploymentError(
                result.stderr.strip() or "Docker Compose configuration is invalid"
            )

        if result.stderr:
            console.print(result.stderr.rstrip(), style="yellow", soft_wrap=True)

        return command

    def setting(self, key: str, default: str = "") -> str:
        """Return a variable as Compose sees it: the shell first, then the env files."""
        if key in os.environ:
            return os.environ[key]

        value = ""

        for env_file in self.env_files:
            value = read_env_file(env_file).get(key, value)

        return value or default

    def up(
        self,
        command: list[str],
        arguments: list[str],
        environment: Environment,
        *,
        process_environment: dict[str, str] | None = None,
    ) -> None:
        """Run ``compose up`` and point to the logs when the services do not start."""
        result = run_command(
            [*command, "up", *arguments], check=False, process_environment=process_environment
        )

        if result.returncode != 0:
            step = current_step()
            where = f" (step {step})" if step else ""
            raise DeploymentError(
                f"{self.title} did not start{where}.\n"
                f"See the logs: infra {self.command_name} logs {environment.value}"
            )

    def statuses(
        self,
        docker: str,
        command: list[str],
        *,
        process_environment: dict[str, str] | None = None,
    ) -> list[ServiceStatus]:
        """Return the state of every service; finished jobs are left out."""
        services = run_command(
            [*command, "config", "--services"],
            capture_output=True,
            process_environment=process_environment,
        ).stdout.split()
        output = run_command(
            [
                docker,
                "ps",
                "--all",
                "--filter",
                f"label=com.docker.compose.project={self.name}",
                "--format",
                '{{.Label "com.docker.compose.service"}}\t{{.State}}\t{{.Status}}',
            ],
            capture_output=True,
        ).stdout
        containers = {
            service: (state, status)
            for line in output.splitlines()
            if line
            for service, state, status in [line.split("\t", 2)]
        }

        statuses: list[ServiceStatus] = []
        for service in sorted(services):
            if service not in containers:
                if service not in self.jobs:
                    statuses.append(ServiceStatus(service, "stopped"))

                continue

            state, status = containers[service]

            if state == "exited":
                code = match["code"] if (match := _EXIT_CODE.search(status)) else "?"

                if service in self.jobs and code == "0":
                    continue

                statuses.append(ServiceStatus(service, f"exited ({code})"))
            else:
                health = match["health"] if (match := _HEALTH.search(status)) else ""
                statuses.append(ServiceStatus(service, state, health))

        return statuses


def find_tool(name: str) -> str:
    executable = shutil.which(name)

    if executable is None:
        raise DeploymentError(f"{name} is not installed or is not available on PATH")

    return executable


def run_command(
    arguments: list[str],
    *,
    check: bool = True,
    capture_output: bool = False,
    process_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=REPOSITORY_ROOT,
        env=process_environment,
        check=check,
        capture_output=capture_output,
        text=True,
    )


def follow_logs(
    command: list[str],
    services: list[str] | None,
    *,
    process_environment: dict[str, str] | None = None,
) -> None:
    run_command(
        [*command, "logs", "--follow", "--tail", "100", *(services or [])],
        process_environment=process_environment,
    )


def network_exists(docker: str, name: str) -> bool:
    result = run_command(
        [docker, "network", "inspect", name],
        check=False,
        capture_output=True,
    )

    return result.returncode == 0


def require_network(docker: str, name: str, recovery: str) -> None:
    if not network_exists(docker, name):
        raise DeploymentError(f"Required Docker network '{name}' does not exist. {recovery}")


def ensure_network(docker: str, name: str) -> None:
    if network_exists(docker, name):
        return

    run_command([docker, "network", "create", "--driver", "bridge", name])


def image_exists(docker: str, image: str) -> bool:
    result = run_command(
        [docker, "image", "inspect", image],
        check=False,
        capture_output=True,
    )

    return result.returncode == 0


def run_cli(app: typer.Typer) -> None:
    try:
        app()
    except DeploymentError as error:
        console.print(f"Error: {error}", style="bold red")
        raise SystemExit(1) from None
    except subprocess.CalledProcessError as error:
        if error.stderr:
            console.print(error.stderr.rstrip(), style="red", soft_wrap=True)
        else:
            console.print(
                f"Error: command failed with exit code {error.returncode}.", style="bold red"
            )
        raise SystemExit(error.returncode) from None
    except KeyboardInterrupt:
        # Ctrl+C ends a foreground command such as watch or logs.
        raise SystemExit(130) from None
