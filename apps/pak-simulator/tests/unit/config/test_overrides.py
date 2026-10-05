from __future__ import annotations

from dataclasses import replace

import pytest

from pak_simulator.config import RunOptionError, configure_run
from pak_simulator.model import Pak, Sessions, Simulation
from pak_simulator.values import Span

pytestmark = pytest.mark.unit


def test_overrides_are_independent_and_preserve_shared_and_unused_profiles(pak: Pak, sessions: Sessions) -> None:
    other_profile = replace(pak.profile, key="other", pass_rate=0.4)
    other_pak = replace(pak, code="OTHER", client_id="other", dev_euis=("0000000000000003",))
    source = Simulation("http://backend", True, sessions, (pak, other_pak), (pak.profile, other_profile))

    configured = configure_run(source, pass_rate=0.25, start_delay="2s..4s", session_delay="500ms")
    another_run = configure_run(source, pass_rate=0)

    assert [item.code for item in configured.paks] == [pak.code, "OTHER"]
    assert configured.paks[0].profile.pass_rate == 0.25
    assert configured.paks[0].profile is configured.paks[1].profile is configured.profiles[0]
    assert configured.profiles[1] is other_profile
    assert configured.sessions.start == Span(2, 4)
    assert configured.sessions.swap == Span(0.5, 0.5)
    assert configured.sessions.retest == sessions.retest
    assert source.paks == (pak, other_pak) and source.profiles == (pak.profile, other_profile)
    assert source.sessions == sessions and other_profile.pass_rate == 0.4
    assert source.paks[0].profile is source.paks[1].profile is pak.profile
    assert another_run.paks[0].profile.pass_rate == 0 and configured.paks[0].profile.pass_rate == 0.25


@pytest.mark.parametrize("pass_rate", [-0.1, 1.1, float("nan"), float("inf"), True])
def test_invalid_probability_reports_its_option(pak: Pak, sessions: Sessions, pass_rate: float) -> None:
    simulation = Simulation("http://backend", True, sessions, (pak,), (pak.profile,))

    with pytest.raises(RunOptionError) as exc:
        configure_run(simulation, pass_rate=pass_rate)

    assert exc.value.option == "--pass-rate"


@pytest.mark.parametrize("delay", ["1s..", "3s..1s", "1s\n"])
def test_invalid_delay_reports_its_option(pak: Pak, sessions: Sessions, delay: str) -> None:
    simulation = Simulation("http://backend", True, sessions, (pak,), (pak.profile,))

    with pytest.raises(RunOptionError) as exc:
        configure_run(simulation, session_delay=delay)

    assert exc.value.option == "--session-delay"
