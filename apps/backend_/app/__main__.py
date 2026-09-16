from __future__ import annotations

import os


def setup_environment() -> None:
    os.environ.setdefault(
        "LITESTAR_APP",
        "app.server.asgi:create_app",
    )


def run_cli() -> None:
    setup_environment()

    from litestar.cli.main import litestar_group

    litestar_group()


if __name__ == "__main__":
    run_cli()
