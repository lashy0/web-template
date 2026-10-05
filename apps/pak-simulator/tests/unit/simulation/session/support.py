"""Build session executors with immediate, cooperative test delays."""

from pak_simulator.contracts import VerificationClient
from pak_simulator.model import Profile, Sessions
from pak_simulator.simulation.session import SessionExecutor
from tests.unit.support import yield_control


def make_executor(
    client: VerificationClient,
    profile: Profile,
    sessions: Sessions,
) -> SessionExecutor:
    return SessionExecutor(
        client,
        profile,
        sessions,
        speed=1,
        sleep=yield_control,
        on_cleanup_error=lambda _: None,
        access_denied=lambda: False,
    )
