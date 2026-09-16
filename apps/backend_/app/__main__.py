from __future__ import annotations

import asyncio
import os
import sys


def setup_environment() -> None:
    os.environ.setdefault(
        "LITESTAR_APP",
        "app.server.asgi:create_app",
    )

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(
            asyncio.WindowsSelectorEventLoopPolicy()
        )



def run_cli() -> None:
    """Application Entrypoint.

    This function sets up the environment and runs the Litestar CLI.
    If there's an error loading the required libraries, it will exit with a status code of 1.
    """
    setup_environment()

    try:
        from litestar.cli.main import litestar_group

        litestar_group()

    except ImportError as exc:
        print( # noqa: T201
            "Could not load required libraries.\n",
            "Please check your installation and make sure you activated any necessary virtual environment",
        )
        print(exc)  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    run_cli()
