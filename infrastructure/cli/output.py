"""Terminal output shared by the infra commands."""

import time
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from rich.console import Console, RenderableType
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

# Messages come from Docker and git as well, so brackets and colons are printed as they are.
console = Console(stderr=True, markup=False, emoji=False, highlight=False)
"""Progress, results and errors."""
_stdout = Console(markup=False, emoji=False, highlight=False)
"""Data a command was asked for, such as the status."""

_step: ContextVar[str | None] = ContextVar("infra_step", default=None)


@contextmanager
def stack_step(number: int, total: int) -> Iterator[None]:
    """Number the headings and errors of one project while the whole stack runs."""
    token = _step.set(f"{number}/{total}")
    try:
        yield
    finally:
        _step.reset(token)


def current_step() -> str | None:
    return _step.get()


def columns(rows: Iterable[Sequence[str | Text]], *, indent: int = 0) -> RenderableType:
    """Lay rows out as left-aligned columns three spaces apart."""
    table = Table.grid(padding=(0, 3, 0, 0))
    for row in rows:
        table.add_row(*row)

    return Padding.indent(table, indent)


def heading(title: str, detail: str | None = None) -> None:
    step = _step.get()
    parts = (f"[{step}]" if step else None, title, detail)
    console.print(" ".join(part for part in parts if part), style="bold cyan")


def announce(message: str) -> None:
    console.print(message, style="bold cyan")


def report(
    verb: str,
    started: float,
    addresses: Sequence[tuple[str, str]] = (),
    *,
    notes: Sequence[str] = (),
) -> None:
    """Print how long a command took, where its services are, and notes; empty notes are skipped."""
    elapsed = round(time.monotonic() - started)
    console.print(f"\n{verb} in {elapsed}s", style="bold green")

    if addresses:
        console.print(columns(addresses, indent=2))

    for note in notes:
        if note:
            console.print(f"\n{note}", style="bold yellow")


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    service: str
    state: str
    health: str = ""


_HEALTH_STYLES = {
    "healthy": "green",
    "unhealthy": "red",
    "starting": "yellow",
}


def _styled_state(state: str) -> Text:
    if state == "running":
        return Text(state)

    if state == "stopped" or state == "exited (0)":
        return Text(state, style="dim")

    return Text(state, style="red" if state.startswith("exited") else "yellow")


def print_status(sections: Sequence[tuple[str, Sequence[ServiceStatus]]]) -> None:
    """Print one row per service, with each project's title on its first row."""
    _stdout.print(
        columns(
            (
                title if index == 0 else "",
                row.service,
                _styled_state(row.state),
                Text(row.health, style=_HEALTH_STYLES.get(row.health, "")),
            )
            for title, rows in sections
            for index, row in enumerate(rows)
        )
    )
