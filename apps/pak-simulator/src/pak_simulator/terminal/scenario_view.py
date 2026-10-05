"""Terminal presentation of a loaded scenario and its profiles."""

from __future__ import annotations

from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pak_simulator.model import Profile, Simulation
from pak_simulator.simulation.state import format_dev_eui


def show_scenario(console: Console, simulation: Simulation, path: Path, *, details: bool = False) -> None:
    header = Table.grid(padding=(0, 2))
    header.add_column(style="dim")
    header.add_column()
    header.add_row("Status", Text("Loaded", style="bold green"))
    header.add_row("File", Text(str(path)))
    console.print(
        Panel.fit(
            header,
            title="Scenario",
            title_align="left",
            border_style="green",
            padding=(0, 1),
        )
    )
    console.line()

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold", no_wrap=True)
    summary.add_column()
    summary.add_row("Server", Text(simulation.server))

    summary.add_row(
        "Loading",
        Text("all slots together" if simulation.sessions.together else "each slot on its own"),
    )

    for item in simulation.paks:
        summary.add_row(
            Text(item.code),
            Text(f"profile {item.profile.key}  ·  {item.slots} slots  ·  {len(item.dev_euis)} units"),
        )
        summary.add_row("DevEUI first", Text(format_dev_eui(item.dev_euis[0])))
        summary.add_row("DevEUI last", Text(format_dev_eui(item.dev_euis[-1])))

    console.print(summary)

    for profile in simulation.profiles:
        console.line()
        console.print(_profile_table(profile, details=details))

        if profile.pass_rate is not None:
            console.print(Text(f"Target pass rate: {profile.pass_rate:.0%} per session.", style="bold cyan"))

        if profile.defects:
            console.line()
            console.print(_defects_table(profile, details=details))

    console.line()


def _profile_table(profile: Profile, *, details: bool = False) -> Table:
    table = Table(
        title=Text(f"Checks · {profile.key} · firmware {profile.firmware_version}", style="bold"),
        title_justify="left",
        box=box.SIMPLE_HEAD,
        pad_edge=False,
        caption_justify="left",
        caption_style="",
    )
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Check", min_width=20, max_width=50, overflow="fold")
    table.add_column("Group", style="dim", no_wrap=True)

    for column in ("Value", "Limits", "Time"):
        table.add_column(column, justify="right", no_wrap=True)

    total = 0.0

    for no, check in enumerate(profile.checks, start=1):
        total += check.time.middle
        value = "—" if check.value is None else _span(check.value.low, check.value.high)

        if check.low is None and check.high is None:
            limits = "—"
        elif check.low is None:
            limits = f"≤ {_number(check.high)}"
        elif check.high is None:
            limits = f"≥ {_number(check.low)}"
        else:
            limits = _span(check.low, check.high)

        label = Text(check.label)

        if check.critical:
            label.append(" *", style="yellow")

        if details:
            label.append(f"\n{check.name}", style="dim")

        table.add_row(
            str(no),
            label,
            Text(check.group),
            f"{value} {check.unit or ''}".strip(),
            limits,
            _span(check.time.low, check.time.high, unit="s"),
        )

    minutes, seconds = divmod(round(total), 60)
    table.caption = Text.assemble(
        (f"Healthy unit: about {minutes} min {seconds:02d} s.", "bold"),
        "\n* A failed critical check ends the session.",
    )

    return table


def _defects_table(profile: Profile, *, details: bool = False) -> Table:
    table = Table(
        title=Text(f"Defects · {profile.key}", style="bold"),
        title_justify="left",
        box=box.SIMPLE_HEAD,
        pad_edge=False,
        caption_justify="left",
        caption_style="",
    )
    table.add_column("Defect", overflow="fold")
    table.add_column("Share", justify="right", no_wrap=True)
    table.add_column("Persists*", justify="right", no_wrap=True)
    table.add_column("Steps", overflow="fold")

    healthy = 1.0

    for defect in profile.defects:
        healthy *= 1 - defect.chance
        label = Text(defect.key.replace("_", " "))

        if details and "_" in defect.key:
            label.append(f"\n{defect.key}", style="dim")

        steps = ", ".join(
            str(no) for no, check in enumerate(profile.checks, start=1) if defect.effect_on(check) is not None
        )
        persists = "every session" if defect.transient else f"{defect.persists:.0%}"
        table.add_row(label, f"{defect.chance:.0%}", persists, steps or "—")

    table.caption = Text.assemble(
        (
            "Defects supply failed check results; pass_rate controls the session outcome."
            if profile.pass_rate is not None
            else f"Sessions with at least one defect: about {1 - healthy:.0%}.",
            "bold",
        ),
        "\n* Chance the defect remains on retest; «every session» is rolled anew for each one.",
        "\nSteps refer to the numbered checks above.",
    )

    return table


def _number(value: float | None) -> str:
    return "" if value is None else f"{value:g}"


def _span(low: float, high: float, *, unit: str = "") -> str:
    text = _number(low) if low == high else f"{_number(low)} to {_number(high)}"

    return f"{text} {unit}".strip()
