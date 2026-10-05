"""Public entry points for terminal rendering and live display."""

from pak_simulator.terminal.dashboard import format_event, render
from pak_simulator.terminal.live import run_live
from pak_simulator.terminal.scenario_view import show_scenario

__all__ = [
    "format_event",
    "render",
    "run_live",
    "show_scenario",
]
