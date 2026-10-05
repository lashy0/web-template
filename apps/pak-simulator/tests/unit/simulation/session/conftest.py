from dataclasses import replace

import pytest

from pak_simulator.contracts import VerificationClient
from pak_simulator.model import Pak, Sessions
from pak_simulator.simulation.session import SessionExecutor
from tests.unit.simulation.session.support import make_executor


@pytest.fixture
def executor(client: VerificationClient, pak: Pak, sessions: Sessions) -> SessionExecutor:
    return make_executor(client, pak.profile, sessions)


@pytest.fixture
def abandoning_executor(client: VerificationClient, pak: Pak, sessions: Sessions) -> SessionExecutor:
    return make_executor(client, pak.profile, replace(sessions, abandon=1))
