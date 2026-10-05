"""Command line: run a scenario, check it, or write its JSON Schema."""

from __future__ import annotations

import asyncio
import json
import math
import signal
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from importlib.metadata import version as package_version
from pathlib import Path
from types import FrameType
from typing import Annotated

import httpx2
import typer
from rich.console import Console
from rich.text import Text

from pak_simulator import preflight
from pak_simulator.application import open_simulation_run
from pak_simulator.client import PakClient
from pak_simulator.config import RunOptionError, ScenarioError, configure_run, load, schema
from pak_simulator.contracts import ClientFactory
from pak_simulator.errors import file_error_message
from pak_simulator.model import Simulation
from pak_simulator.simulation.state import Event, EventLog, RunResult
from pak_simulator.terminal import format_event, run_live, show_scenario

console = Console(highlight=False)

ScenarioPath = Annotated[Path, typer.Argument(help="Scenario YAML file.", show_default=False)]


def _load(path: Path, *, server: str | None = None, pak_codes: Sequence[str] | None = None) -> Simulation:
    try:
        return load(path, server=server, pak_codes=pak_codes)
    except ScenarioError as exc:
        console.print(Text(str(exc), style="red"))
        raise typer.Exit(1) from None


class Commands:
    def __init__(
        self,
        client_factory: ClientFactory,
        health_transport: httpx2.AsyncBaseTransport | None,
    ) -> None:
        self._client_factory = client_factory
        self._health_transport = health_transport

    def run(
        self,
        path: ScenarioPath,
        speed: Annotated[
            float,
            typer.Option(min=0.1, max=100, help="Run time this many times faster."),
        ] = 1.0,
        server: Annotated[
            str | None,
            typer.Option(help="Application address instead of the one in the scenario."),
        ] = None,
        pak: Annotated[
            list[str] | None,
            typer.Option(help="Run only this PAK of the scenario, by code; repeatable."),
        ] = None,
        once: Annotated[
            bool,
            typer.Option("--once", help="Verify each unit once instead of cycling through them."),
        ] = False,
        seed: Annotated[
            int | None,
            typer.Option(help="Seed for a repeatable run."),
        ] = None,
        live: Annotated[
            bool,
            typer.Option("--live/--log", help="Live slot table or event log."),
        ] = True,
        pass_rate: Annotated[
            float | None,
            typer.Option(min=0, max=1, help="Probability of a passed session; overrides the profile."),
        ] = None,
        start_delay: Annotated[
            str | None,
            typer.Option(help="Initial slot delay, e.g. 0s..2s; scaled by --speed."),
        ] = None,
        session_delay: Annotated[
            str | None,
            typer.Option(help="Delay between sessions, e.g. 1s..3s; scaled by --speed."),
        ] = None,
    ) -> None:
        """Run the PAKs until Ctrl+C, SIGTERM, or the scenario ends with --once."""
        if not math.isfinite(speed):
            raise typer.BadParameter("Speed must be a finite number.", param_hint="--speed")

        simulation = _load(path, server=server, pak_codes=pak)

        try:
            simulation = configure_run(
                simulation, pass_rate=pass_rate, start_delay=start_delay, session_delay=session_delay
            )
        except RunOptionError as exc:
            raise typer.BadParameter(str(exc), param_hint=exc.option) from exc

        events = EventLog(sink=None if live else _print_event)

        try:
            results = asyncio.run(
                _run(
                    simulation,
                    events,
                    speed=speed,
                    loop=not once,
                    seed=seed,
                    live=live,
                    client_factory=self._client_factory,
                )
            )
        except (KeyboardInterrupt, asyncio.CancelledError):
            if live:
                # The live table leaves the cursor at the end of its last line.
                console.line()

            console.print(Text("Stopped.", style="bright_black"))
            raise typer.Exit(130) from None
        else:
            _report_results(results)

    def check(
        self,
        path: ScenarioPath,
        details: Annotated[
            bool,
            typer.Option(help="Also show technical check names."),
        ] = False,
        offline: Annotated[
            bool,
            typer.Option(help="Check only the scenario, without contacting the server."),
        ] = False,
        server: Annotated[
            str | None,
            typer.Option(help="Application address instead of the one in the scenario."),
        ] = None,
    ) -> None:
        """Check the scenario, server health and PAK client credentials."""
        simulation = _load(path, server=server)

        console.line()
        show_scenario(console, simulation, path, details=details)

        if offline:
            console.print(Text("Configuration checked. Server checks skipped (--offline).", style="dim"))

            return

        console.print(Text("Online checks", style="bold cyan"))

        try:
            passed = asyncio.run(
                _check_remote(
                    simulation,
                    client_factory=self._client_factory,
                    health_transport=self._health_transport,
                )
            )
        except KeyboardInterrupt:
            console.print(Text("Check interrupted.", style="yellow"))
            raise typer.Exit(130) from None

        console.line()
        console.print(Text("No verification sessions were created or changed.", style="dim"))

        if not passed:
            raise typer.Exit(1)


def _report_results(results: Sequence[RunResult]) -> None:
    failed = [item for item in results if not item.successful]

    if failed:
        codes = ", ".join(item.pak_code for item in failed)
        errors = sum(item.execution_errors for item in failed)
        unfinished = sum(item.unfinished_units for item in failed)
        console.print(
            Text(
                f"Simulation ended with errors. PAKs: {codes}. Execution errors: {errors}; unfinished units: {unfinished}.",
                style="red",
            )
        )
        raise typer.Exit(1)

    console.print(Text("Simulation complete: all selected PAKs finished.", style="bold cyan"))


async def _run(
    simulation: Simulation,
    events: EventLog,
    *,
    speed: float,
    loop: bool,
    seed: int | None,
    live: bool,
    client_factory: ClientFactory = PakClient,
) -> tuple[RunResult, ...]:

    with _cancel_on_sigterm():
        async with open_simulation_run(
            simulation,
            events,
            speed=speed,
            loop=loop,
            seed=seed,
            client_factory=client_factory,
        ) as execution:
            console.line()

            if live:
                results = await run_live(execution, events, console=console, speed=speed)
            else:
                console.print(f"Server {simulation.server}, PAKs: {', '.join(item.code for item in simulation.paks)}")
                results = await execution.execute()

    return results


@contextmanager
def _cancel_on_sigterm() -> Iterator[None]:
    """Cancel the run task on SIGTERM so its async cleanup can abort sessions."""
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()

    if task is None:
        raise RuntimeError("SIGTERM handling requires an active asyncio task")

    previous = signal.getsignal(signal.SIGTERM)

    def cancel_run(_signum: int, _frame: FrameType | None) -> None:
        loop.call_soon_threadsafe(task.cancel)

    signal.signal(signal.SIGTERM, cancel_run)

    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def _print_event(event: Event) -> None:
    origin, text = format_event(event)
    console.print(origin, text)


async def _check_remote(
    simulation: Simulation,
    *,
    client_factory: ClientFactory,
    health_transport: httpx2.AsyncBaseTransport | None,
) -> bool:
    passed = True
    with console.status("Starting online checks...", spinner="dots", spinner_style="cyan") as status:

        def show_stage(stage: str) -> None:
            message = Text.assemble(("Online check", "bold cyan"), " · ", stage, "...")
            status.update(message)

            if not console.is_terminal:
                console.print(message)

        async for probe in preflight.check_remote(
            simulation,
            on_start=show_stage,
            client_factory=client_factory,
            health_transport=health_transport,
        ):
            console.print(
                Text.assemble(
                    (f"{probe.status:<5}", "green" if probe.status == "OK" else "red"),
                    "  ",
                    (probe.target, "bold"),
                    "  ",
                    probe.detail,
                )
            )
            passed = passed and probe.status == "OK"

    return passed


def write_schema(
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="File to write; stdout without it."),
    ] = None,
) -> None:
    """Write the scenario JSON Schema for editor completion."""
    text = json.dumps(schema(), ensure_ascii=False, indent=2) + "\n"

    if output is None:
        typer.echo(text, nl=False)
    else:
        try:
            output.write_text(text, encoding="utf-8", newline="\n")
        except OSError as exc:
            console.print(Text(file_error_message(exc, output, action="write"), style="red"))
            raise typer.Exit(1) from None

        console.print(f"Schema written to {output}")


def _show_version(value: bool) -> None:
    if value:
        typer.echo(f"pak-sim {package_version('pak-simulator')}")
        raise typer.Exit()


def cli_options(
    _version: Annotated[
        bool,
        typer.Option("--version", "-V", callback=_show_version, is_eager=True, help="Show the version and exit."),
    ] = False,
) -> None:
    """Global options shared by the simulator commands."""


def create_app(
    *,
    client_factory: ClientFactory = PakClient,
    health_transport: httpx2.AsyncBaseTransport | None = None,
) -> typer.Typer:
    commands = Commands(client_factory, health_transport)
    application = typer.Typer(
        add_completion=False,
        no_args_is_help=True,
        help="PAK simulator for live demos of the verification screens.",
    )
    application.callback()(cli_options)
    application.command("run")(commands.run)
    application.command("check")(commands.check)
    application.command("schema")(write_schema)

    return application


app = create_app()


def main() -> None:
    app()
