import typer

from cli.backend import backend_app
from cli.compose import run_cli
from cli.frontend import frontend_app

app = typer.Typer(
    help="Manage the application frontend and backend.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(backend_app, name="backend")
app.add_typer(frontend_app, name="frontend")


def main() -> None:
    run_cli(app)


if __name__ == "__main__":
    main()
