"""Pongogo CLI entry point."""

import typer
from rich.console import Console

from . import __version__
from .init_command import init_command

app = typer.Typer(
    name="pongogo",
    help="Pongogo - AI agent knowledge routing for your repository",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"pongogo version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Pongogo - AI agent knowledge routing for your repository."""
    pass


# Register the init command
app.command(name="init")(init_command)


if __name__ == "__main__":
    app()
