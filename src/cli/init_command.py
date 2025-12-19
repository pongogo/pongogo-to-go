"""The pongogo init command implementation."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from .config import generate_config, write_config
from .instructions import (
    copy_instructions,
    copy_manifest,
    get_enabled_categories,
    get_package_instructions_dir,
    load_manifest,
)

console = Console()

PONGOGO_DIR = ".pongogo"
CONFIG_FILE = "config.yaml"
INSTRUCTIONS_DIR = "instructions"


def init_command(
    minimal: bool = typer.Option(
        False,
        "--minimal",
        "-m",
        help="Only install core instruction categories (software_engineering, safety_prevention)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing .pongogo directory",
    ),
    no_interactive: bool = typer.Option(
        False,
        "--no-interactive",
        "-y",
        help="Accept all defaults without prompting",
    ),
) -> None:
    """Initialize Pongogo in the current directory.

    Creates a .pongogo/ directory with configuration and seeded instruction files.
    """
    cwd = Path.cwd()
    pongogo_dir = cwd / PONGOGO_DIR

    # Check for existing installation
    if pongogo_dir.exists():
        if not force:
            console.print(
                f"[red]Error:[/red] {PONGOGO_DIR}/ already exists. "
                "Use --force to overwrite.",
                style="bold",
            )
            raise typer.Exit(1)
        else:
            console.print(f"[yellow]Overwriting existing {PONGOGO_DIR}/ directory...[/yellow]")
            import shutil
            shutil.rmtree(pongogo_dir)

    # Show welcome message
    console.print(
        Panel(
            "[bold blue]Pongogo[/bold blue] - AI agent knowledge routing\n\n"
            "This will create a .pongogo/ directory with:\n"
            "  - config.yaml (configuration)\n"
            "  - instructions/ (seeded instruction files)",
            title="Initializing Pongogo",
            border_style="blue",
        )
    )

    # Interactive mode: prompt for options
    if not no_interactive and not minimal:
        minimal = typer.confirm(
            "Use minimal installation (core instructions only)?",
            default=False,
        )

    # Generate configuration
    console.print("\n[bold]Creating configuration...[/bold]")
    config = generate_config(minimal=minimal)

    config_path = pongogo_dir / CONFIG_FILE
    write_config(config_path, config)
    console.print(f"  [green]Created[/green] {PONGOGO_DIR}/{CONFIG_FILE}")

    # Copy instruction files
    console.print("\n[bold]Copying instruction files...[/bold]")

    try:
        source_dir = get_package_instructions_dir()
        manifest = load_manifest(source_dir)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    dest_instructions_dir = pongogo_dir / INSTRUCTIONS_DIR
    enabled_categories = get_enabled_categories(manifest, config["categories"])

    files_copied = copy_instructions(
        source_dir=source_dir,
        dest_dir=dest_instructions_dir,
        manifest=manifest,
        enabled_categories=enabled_categories,
    )

    # Copy manifest
    copy_manifest(source_dir, dest_instructions_dir)

    console.print(f"  [green]Copied[/green] {files_copied} instruction files")
    console.print(f"  [green]Categories:[/green] {', '.join(enabled_categories)}")

    # Success message
    console.print(
        Panel(
            f"[green]Pongogo initialized successfully![/green]\n\n"
            f"Created: {PONGOGO_DIR}/\n"
            f"  - {CONFIG_FILE}\n"
            f"  - {INSTRUCTIONS_DIR}/ ({files_copied} files)\n\n"
            "[dim]Next steps:[/dim]\n"
            "  1. Review and customize .pongogo/config.yaml\n"
            "  2. Configure MCP server for Claude Code integration\n"
            "  3. See https://github.com/pongogo/pongogo-to-go for documentation",
            title="Success",
            border_style="green",
        )
    )
