import argparse
import json
from pathlib import Path
from typing import cast

from fastapi import FastAPI

from app.main import create_app


def export_openapi(app: FastAPI, output: Path) -> None:
    """Write the application's complete OpenAPI document to ``output``."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_output() -> Path:
    parser = argparse.ArgumentParser(
        description="Export the complete backend OpenAPI document.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination for the OpenAPI JSON document.",
    )
    return cast(Path, parser.parse_args().output)


def main() -> None:
    output = parse_output()
    export_openapi(create_app(), output)


if __name__ == "__main__":
    main()
