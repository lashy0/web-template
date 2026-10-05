from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from pak_simulator.model import Check, Pak, Profile, Retest, Sessions
from pak_simulator.values import Span
from tests.unit.support import make_client, make_client_factory


@pytest.fixture
def scenario_data() -> dict[str, Any]:
    return {
        "server": "http://backend",
        "paks": [
            {
                "code": "P",
                "client_id": "c",
                "access_key": "k",
                "profile": "p",
                "slots": 1,
                "dev_eui": ["0000000000000001"],
            }
        ],
        "profiles": {
            "p": {
                "firmware_version": "1",
                "checks": [{"name": "test", "label": "Test", "group": "G", "time": 0, "value": 1}],
            }
        },
    }


@pytest.fixture
def pak() -> Pak:
    check = Check("test", "Test", "G", Span(0, 0), Span(1, 1), None, None, None, False)
    profile = Profile("p", "1", (check, check, check), (), pass_rate=1)

    return Pak("PAK", "client", "secret", 2, profile, ("0000000000000001", "0000000000000002"))


@pytest.fixture
def sessions() -> Sessions:
    return Sessions(Span(0, 0), Span(0, 0), 0, Retest(0, 0, 1, Span(0, 0)))


@pytest.fixture
def client() -> AsyncMock:
    return make_client()


@pytest.fixture
def client_factory(client: AsyncMock) -> Mock:
    return make_client_factory(client)
