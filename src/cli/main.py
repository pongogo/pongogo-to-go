"""Pongogo CLI entry point."""

import shutil

import typer

from . import __version__
from .console import console, print_error, print_success, print_warning
from .discoveries import app as discoveries_app
from .init_command import init_command
from .setup_mcp import setup_mcp_command
from .uninstall import (
    remove_from_claude_mcp_json,
    remove_from_global_claude_json,
    remove_from_mcp_json,
    remove_hooks_from_settings,
)

app = typer.Typer(
    name="pongogo",
    help="Pongogo - AI agent knowledge routing for your repository",
    no_args_is_help=True,
)


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

# Register the setup-mcp command
app.command(name="setup-mcp")(setup_mcp_command)

# Register the discoveries subcommand group
app.add_typer(discoveries_app, name="discoveries")


PONGOGO_IMAGE = "pongogo.azurecr.io/pongogo:stable"


@app.command(name="uninstall")
def uninstall_command(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
    remove_image: bool = typer.Option(
        False,
        "--remove-image",
        help="Also remove the Docker image",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug output",
    ),
) -> None:
    """Uninstall Pongogo from the current project.

    Removes:
    - .pongogo/ directory (instructions and config)
    - .mcp.json MCP server configuration
    - .claude/mcp.json MCP server configuration
    - .claude/settings.local.json hooks
    - ~/.claude.json global configuration (if present)

    With --remove-image, also removes the Docker image.
    """
    import subprocess
    from pathlib import Path

    # Check if .pongogo exists
    pongogo_dir = Path(".pongogo")
    if not pongogo_dir.exists():
        print_warning("No .pongogo directory found - Pongogo may not be installed here")
        if not force:
            raise typer.Exit(0)

    # Confirm unless --force
    if not force:
        console.print("\n[bold]This will remove:[/bold]")
        console.print("  • .pongogo/ directory")
        console.print("  • MCP server configuration from .mcp.json")
        console.print("  • MCP server configuration from .claude/mcp.json")
        console.print("  • Hooks from .claude/settings.local.json")
        console.print("  • Global config from ~/.claude.json (if present)")
        if remove_image:
            console.print(f"  • Docker image: {PONGOGO_IMAGE}")
        console.print("")

        confirm = typer.confirm("Continue with uninstall?")
        if not confirm:
            console.print("Uninstall cancelled.")
            raise typer.Exit(0)

    console.print("")
    success = True

    # Remove .pongogo directory
    if pongogo_dir.exists():
        try:
            shutil.rmtree(pongogo_dir)
            print_success("Removed .pongogo/ directory")
        except Exception as e:
            print_error(f"Failed to remove .pongogo/: {e}")
            success = False

    # Remove from .mcp.json
    if not remove_from_mcp_json(".mcp.json", debug):
        success = False

    # Remove from .claude/mcp.json
    if not remove_from_claude_mcp_json(debug):
        success = False

    # Remove hooks from settings
    if not remove_hooks_from_settings(debug):
        success = False

    # Remove from global config
    if not remove_from_global_claude_json(debug):
        success = False

    # Remove Docker image if requested
    if remove_image:
        try:
            result = subprocess.run(
                ["docker", "rmi", PONGOGO_IMAGE],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print_success(f"Removed Docker image: {PONGOGO_IMAGE}")
            elif "No such image" in result.stderr:
                print_success("Docker image not present (already removed)")
            else:
                print_error(f"Failed to remove Docker image: {result.stderr.strip()}")
                success = False
        except FileNotFoundError:
            print_warning("Docker not found - skipping image removal")
        except Exception as e:
            print_error(f"Failed to remove Docker image: {e}")
            success = False

    console.print("")
    if success:
        print_success("Pongogo uninstalled successfully")
    else:
        print_error("Uninstall completed with errors")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
