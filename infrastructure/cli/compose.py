import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import typer

INFRASTRUCTURE_ROOT = Path(__file__).resolve().parent.parent
REPOSITORY_ROOT = INFRASTRUCTURE_ROOT.parent
ROOT_ENV_FILE = REPOSITORY_ROOT / ".env"


class Environment(StrEnum):
    DEV = "dev"
    PROD = "prod"


class DeploymentError(RuntimeError):
    """An expected operational error that can be shown without a traceback."""


@dataclass(frozen=True, slots=True)
class ComposeProject:
    root: Path
    env_files: tuple[Path, ...] = (ROOT_ENV_FILE,)

    def prepare(
        self,
        docker: str,
        environment: Environment,
        *,
        process_environment: dict[str, str] | None = None,
    ) -> list[str]:
        for env_file in self.env_files:
            if not env_file.is_file():
                raise DeploymentError(f"Environment file does not exist: {env_file}")

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
            typer.secho(result.stderr.rstrip(), fg=typer.colors.YELLOW, err=True)
        return command


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


def run_cli(app: typer.Typer) -> None:
    try:
        app()
    except DeploymentError as error:
        typer.secho(f"Error: {error}", fg=typer.colors.RED, bold=True, err=True)
        raise SystemExit(1) from None
    except subprocess.CalledProcessError as error:
        if error.stderr:
            typer.secho(error.stderr.rstrip(), fg=typer.colors.RED, err=True)
        else:
            typer.secho(
                f"Error: command failed with exit code {error.returncode}.",
                fg=typer.colors.RED,
                bold=True,
                err=True,
            )
        raise SystemExit(error.returncode) from None
