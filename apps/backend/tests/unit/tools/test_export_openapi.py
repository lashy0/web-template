import json
from pathlib import Path

import pytest

from app.main import create_app
from tools.export_openapi import export_openapi


@pytest.mark.unit
def test_export_openapi_writes_the_application_schema(tmp_path: Path) -> None:
    app = create_app()
    output = tmp_path / "generated" / "openapi.json"

    export_openapi(app, output)

    assert json.loads(output.read_text(encoding="utf-8")) == app.openapi()
    assert output.read_bytes().endswith(b"\n")
