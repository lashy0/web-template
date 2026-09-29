"""The ``infra`` command: the whole stack at once, or each Compose project alone."""

import time
from collections.abc import Callable

import typer

from cli import backend, database, frontend, identity, traefik
from cli.compose import DeploymentError, Environment, EnvironmentArgument, run_cli
from cli.init import init
from cli.output import print_status, report, stack_step
from cli.release import release

app = typer.Typer(
    help="Manage the OTK App infrastructure.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(database.database_app, name="database")
app.add_typer(traefik.traefik_app, name="traefik")
app.add_typer(identity.identity_app, name="identity")
app.add_typer(backend.backend_app, name="backend")
app.add_typer(frontend.frontend_app, name="frontend")
app.command()(init)
app.command()(release)

STARTS: tuple[Callable[[Environment], str | None], ...] = (
    database.start,
    traefik.start,
    identity.start,
    backend.start,
    frontend.start,
)
"""Start each project in order; a returned text is shown after the summary."""
STOPS = (frontend.stop, backend.stop, identity.stop, traefik.stop, database.stop)
STATUSES = (
    database.status_section,
    traefik.status_section,
    identity.status_section,
    backend.status_section,
    frontend.status_section,
)


@app.command()
def up(environment: EnvironmentArgument, watch: backend.WatchOption = False) -> None:
    """Start every project in dependency order."""
    if watch and environment is not Environment.DEV:
        raise DeploymentError("--watch is available only for the dev environment.")

    started = time.monotonic()
    notes: list[str] = []

    for number, start in enumerate(STARTS, 1):
        with stack_step(number, len(STARTS)):
            if note := start(environment):
                notes.append(note)
    report(
        "Ready",
        started,
        [
            *frontend.addresses(environment),
            *backend.addresses(environment),
            *traefik.addresses(environment),
        ],
        notes=notes,
    )

    if watch:
        backend.watch_changes(environment)


@app.command()
def down(environment: EnvironmentArgument) -> None:
    """Stop every project in reverse dependency order, keeping the data volumes."""
    started = time.monotonic()

    for number, stop in enumerate(STOPS, 1):
        with stack_step(number, len(STOPS)):
            stop(environment)

    report("Stopped", started)


@app.command()
def status(environment: EnvironmentArgument) -> None:
    """Show the state of every service."""
    print_status([section(environment) for section in STATUSES])


def main() -> None:
    run_cli(app)


if __name__ == "__main__":
    main()
