"""The live screen: PAK slots, totals and recent events."""

from __future__ import annotations

from collections.abc import Sequence
from math import ceil
from time import monotonic
from typing import cast

from rich import box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from pak_simulator.simulation.state import (
    Event,
    EventLogSnapshot,
    PakSnapshot,
    PakStatus,
    SlotSnapshot,
    SlotStatus,
    format_dev_eui,
)

_PAK_STATUS = {
    PakStatus.RUNNING: ("Running", "bold blue"),
    PakStatus.WAITING: ("Waiting between loads", "bold cyan"),
    PakStatus.FINISHED: ("Finished", "bold cyan"),
    PakStatus.STOPPED: ("Stopped", "bold yellow"),
    PakStatus.ERROR: ("Error", "bold red"),
}

_STATUS = {
    SlotStatus.WAITING: ("◌ Waiting", "bright_black"),
    SlotStatus.RUNNING: ("● Running", "blue"),
    SlotStatus.PASSED: ("✓ Passed", "green"),
    SlotStatus.FAILED: ("✗ Failed", "red"),
    SlotStatus.ABANDONED: ("- Incomplete", "yellow"),
    SlotStatus.ABORTED: ("■ Aborted", "yellow"),
    SlotStatus.ERROR: ("! Error", "red"),
    SlotStatus.DONE: ("◌ Free", "bright_black"),
}

_LEVEL_STYLES = {"info": "", "warning": "yellow", "error": "red"}
_RUNNING_SPINNER = Spinner("dots", style="bold blue")


def render(runs: Sequence[PakSnapshot], events: EventLogSnapshot, *, speed: float) -> RenderableType:
    parts: list[RenderableType] = []

    for run in runs:
        parts.extend((_pak_panel(run, speed=speed), Text("")))

    parts.append(_events(events.recent, limit=events.limit))

    if any(run.status in (PakStatus.RUNNING, PakStatus.WAITING) for run in runs):
        parts.append(Text(""))
        parts.append(Text("Ctrl+C to stop; running sessions are aborted", style="bright_black"))

    return Group(*parts)


def _pak_panel(run: PakSnapshot, *, speed: float) -> Panel:
    status = run.status
    label, style = _PAK_STATUS[status]
    status_text = Text(label, style=style)

    if status is PakStatus.RUNNING:
        status_text = cast(Text, _RUNNING_SPINNER.render(monotonic()))
        status_text.append(f" {label}", style=style)

    header = Text.assemble(
        ("Status: ", "bright_black"),
        status_text,
        (
            f"\nProfile: {run.profile_key} · Units: {run.total_units} · Slots: {len(run.slots)}",
            "bright_black",
        ),
        (f" · Speed: x{speed:g}" if speed != 1 else "", "bright_black"),
    )

    if run.pass_rate is not None:
        header.append(f" · Target pass rate: {run.pass_rate:.0%}", style="bright_black")

    progress = (
        f"Attempts processed: {run.stats.attempts_processed} · Loop"
        if run.looping
        else f"Units: {run.processed_units}/{run.total_units} processed"
    )
    header.append(f"\n{progress} · {run.running_units} running · {run.waiting_units} queued", style="cyan")

    if run.alert:
        header.append(f"\n{run.alert}", style="bold red")

    border = "bright_black"

    if status in (PakStatus.RUNNING, PakStatus.WAITING):
        border = "blue"
    elif status is PakStatus.ERROR:
        border = "red"

    return Panel.fit(
        Group(header, _pak_table(run)),
        title=Text(run.code, style="bold"),
        title_align="left",
        border_style=border,
        padding=(0, 1),
    )


def _pak_table(run: PakSnapshot) -> Table:
    table = Table(
        caption=_totals(run),
        caption_justify="left",
        box=box.SIMPLE_HEAD,
        expand=False,
        pad_edge=False,
    )
    table.add_column("Slot", justify="right")
    table.add_column("KG unit", no_wrap=True)
    table.add_column("Steps", no_wrap=True)
    table.add_column("Time", justify="right")
    table.add_column("Status", no_wrap=True)
    table.add_column("Details", width=28, max_width=28, overflow="ellipsis", no_wrap=True)

    for slot in run.slots:
        label, style = _STATUS[slot.status]
        table.add_row(
            str(slot.no),
            _unit(slot),
            _progress(slot),
            _elapsed(slot),
            Text(label, style=style),
            _details(slot),
        )

    return table


def _unit(slot: SlotSnapshot) -> Text:
    if slot.dev_eui is None:
        return Text("—", style="bright_black")

    text = Text(format_dev_eui(slot.dev_eui))

    if slot.attempt > 1:
        text.append(f"  #{slot.attempt}", style="yellow")

    return text


def _progress(slot: SlotSnapshot) -> Text:
    if not slot.total_steps:
        return Text("")

    text = Text()

    for passed in slot.outcomes:
        text.append("▰", style="green" if passed else "red")

    remaining = slot.total_steps - len(slot.outcomes)

    if slot.status is SlotStatus.RUNNING and remaining:
        text.append("▰", style="blue")
        remaining -= 1

    text.append("▱" * remaining, style="bright_black")
    text.append(f" {len(slot.outcomes)}/{slot.total_steps}", style="bright_black")

    return text


def _elapsed(slot: SlotSnapshot) -> str:
    elapsed = slot.elapsed

    if elapsed is None:
        return ""

    minutes, seconds = divmod(int(elapsed), 60)

    return f"{minutes}:{seconds:02d}"


def _details(slot: SlotSnapshot) -> Text:
    if (remaining := slot.next_session_in) is not None:
        minutes, seconds = divmod(ceil(remaining), 60)

        return Text(f"Next session in {minutes}:{seconds:02d}", style="cyan")

    if slot.status is SlotStatus.RUNNING:
        return Text(slot.step_label)

    if slot.status is SlotStatus.FAILED:
        return Text(slot.failure_summary, style="red")

    return Text(slot.note, style="bright_black")


def _totals(run: PakSnapshot) -> Text:
    text = Text("Run summary: ", style="bold")
    stats = run.stats
    added = False

    for count, label, style, always_show in (
        (stats.passed, "Passed", "green", True),
        (stats.failed, "Failed", "red", True),
        (stats.abandoned, "Incomplete", "yellow", False),
        (stats.skipped, "Skipped", "bright_black", False),
        (stats.errors, "Errors", "red", False),
        (stats.cleanup_errors, "Cleanup errors", "red", False),
        (stats.internal_errors, "Internal errors", "red", False),
    ):
        if not count and not always_show:
            continue

        if added:
            text.append(" · ", style="bright_black")

        text.append(f"{label} {count}", style=style)
        added = True

    rate = run.actual_pass_rate
    text.append(f" · Actual pass rate: {rate:.0%}" if rate is not None else " · Actual pass rate: —", style="cyan")

    if (remaining := run.next_load_in) is not None:
        minutes, seconds = divmod(ceil(remaining), 60)

        if text:
            text.append("\n")

        text.append(
            f"Next batch of units in {minutes}:{seconds:02d} · Units queued: {run.queued_units}",
            style="bold cyan",
        )

    return text


def _events(recent: Sequence[Event], *, limit: int | None) -> RenderableType:
    title = f"Recent events (last {limit})" if limit is not None else "Recent events"
    table = Table(title=Text(title, style="bold"), title_justify="left", box=box.SIMPLE_HEAD, pad_edge=False)
    table.add_column("Time", style="bright_black", no_wrap=True)
    table.add_column("PAK", style="bright_black", no_wrap=True)
    table.add_column("Slot", style="bright_black", justify="right", no_wrap=True)
    table.add_column("KG unit", no_wrap=True)
    table.add_column("Result", no_wrap=True)
    table.add_column("Details", overflow="fold")

    for event in recent:
        result = Text("—", style="bright_black")

        if event.result is not None:
            label, style = _STATUS[event.result]
            result = Text(label, style=style)

        table.add_row(
            f"{event.at:%H:%M:%S}",
            event.pak,
            str(event.slot) if event.slot is not None else "—",
            format_dev_eui(event.dev_eui) if event.dev_eui else "—",
            result,
            Text(event.text, style=_LEVEL_STYLES[event.level]),
        )

    if not recent:
        table.add_row("—", "—", "—", "—", "—", Text("No events yet", style="bright_black"))

    return table


def format_event(event: Event) -> tuple[Text, Text]:
    origin = event.pak if event.slot is None else f"{event.pak} · slot {event.slot}"
    message = Text(style=_LEVEL_STYLES[event.level])

    if event.dev_eui:
        message.append(f"{format_dev_eui(event.dev_eui)} — ")

    if event.result is not None:
        label, style = _STATUS[event.result]
        message.append(label, style=style)
        message.append(" · ")

    message.append(event.text)

    return (
        Text(f"{event.at:%H:%M:%S}  {origin}", style="bright_black"),
        message,
    )
