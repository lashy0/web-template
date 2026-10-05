"""Independent random streams for outcomes and scheduling."""

from __future__ import annotations

import hashlib
import json
import random

from pak_simulator.simulation.state import Unit


class RandomStreams:
    def __init__(self, seed: int, pak_code: str) -> None:
        self._seed = seed
        self._pak_code = pak_code

    def _stream(self, *parts: str | int) -> random.Random:
        identity = json.dumps([self._seed, self._pak_code, *parts], ensure_ascii=False).encode()

        return random.Random(hashlib.blake2b(identity, digest_size=16).digest())

    def session(self, unit: Unit) -> random.Random:
        return self._stream("session", unit.dev_eui, unit.cycle, unit.attempt + 1)

    def retest(self, unit: Unit) -> random.Random:
        return self._stream("retest", unit.dev_eui, unit.cycle, unit.attempt)

    def schedule(self, slot_no: int) -> random.Random:
        return self._stream("schedule", slot_no)
