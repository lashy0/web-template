from __future__ import annotations

from pathlib import Path
from typing import Any

import msgspec


def write_scenario(tmp_path: Path, data: dict[str, Any]) -> Path:
    path = tmp_path / "scenario.yaml"
    path.write_bytes(msgspec.yaml.encode(data))

    return path
