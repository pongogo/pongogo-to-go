"""Setup MCP server integration with Claude Code."""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import typer

from .console import RICH_AVAILABLE, console


def has_docker() -> bool:
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_claude_config_path() -> Path:
    """Get path to Claude Code configuration file."""
    return Path.home() / ".claude.json"


def get_mcp_config() -> dict:
    """Generate MCP server configuration for Claude Code.

    Currently requires Docker for guaranteed multi-repo isolation.
    The ${workspaceFolder} variable expansion in Docker volume mounts
    ensures each workspace gets its own isolated .pongogo directory.

    Note: Direct Python installation (pip) is not yet supported because
    Claude Code's ${workspaceFolder} variable expansion in the `env`
    section is unverified. See GitHub issue for tracking.
    """
    # Docker-based configuration (required for multi-repo isolation)
    config = {
        "command": "docker",
        "args": [
            "run",
            "-i",
            "--rm",
            "-v",
            "${workspaceFolder}/.pongogo:/project/.pongogo:ro",
            "ghcr.io/pongogo/pongogo-server:latest",
        ],
    }

    return config


def load_claude_config(path: Path) -> dict:
    """Load existing Claude Code configuration or return default."""
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except json.JSONDecodeError:
            console.print(
                "[yellow]Warning: Could not parse existing config, starting fresh[/yellow]"
            )
    return {}


def backup_config(path: Path) -> Path | None:
    """Create backup of existing config file."""
    if path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_suffix(f".backup_{timestamp}.json")
        shutil.copy(path, backup_path)
        return backup_path
    return None


def merge_mcp_config(existing: dict, new_server_config: dict) -> dict:
    """Merge new MCP server config into existing Claude config."""
    # Ensure mcpServers key exists
    if "mcpServers" not in existing:
        existing["mcpServers"] = {}

    # Add/update pongogo server
    existing["mcpServers"]["pongogo-knowledge"] = new_server_config

    return existing


def setup_mcp_command(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be done without making changes",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing pongogo configuration if present",
    ),
) -> None:
    """Configure Claude Code to use Pongogo MCP server.

    Requires Docker for guaranteed multi-repo isolation. Each workspace
    gets its own isolated .pongogo directory via volume mounts.
    """
    # Docker is required for multi-repo isolation
    if not has_docker():
        console.print("[red]Error: Docker is required for Pongogo MCP server.[/red]")
        console.print("\nDocker ensures proper isolation when using Pongogo across")
        console.print("multiple repositories on the same machine.")
        console.print("\n[bold]To install Docker:[/bold]")
        console.print("  macOS: brew install --cask docker")
        console.print("  Linux: https://docs.docker.com/engine/install/")
        console.print(
            "  Windows: https://docs.docker.com/desktop/install/windows-install/"
        )
        console.print("\nAfter installing, ensure Docker is running and try again.")
        raise typer.Exit(1)

    config_path = get_claude_config_path()
    mcp_config = get_mcp_config()

    # Load existing config
    existing_config = load_claude_config(config_path)

    # Check if pongogo already configured
    if (
        "mcpServers" in existing_config
        and "pongogo-knowledge" in existing_config["mcpServers"]
        and not force
    ):
        console.print("[yellow]Pongogo MCP server already configured.[/yellow]")
        console.print("Use --force to overwrite existing configuration.")
        raise typer.Exit(1)

    # Merge configuration
    merged_config = merge_mcp_config(existing_config.copy(), mcp_config)

    if dry_run:
        console.print("[bold]Dry run - no changes made[/bold]\n")
        console.print(f"Config path: {config_path}")
        console.print("Method: Docker (required for multi-repo isolation)\n")
        console.print("[bold]Configuration to add:[/bold]")
        config_json = json.dumps(
            {"mcpServers": {"pongogo-knowledge": mcp_config}}, indent=2
        )
        if RICH_AVAILABLE:
            console.print_json(config_json)
        else:
            print(config_json)
        return

    # Create backup
    backup_path = backup_config(config_path)
    if backup_path:
        console.print(f"[dim]Backup created: {backup_path}[/dim]")

    # Write merged config
    with open(config_path, "w") as f:
        json.dump(merged_config, f, indent=2)

    # Success message
    console.print("[green]Pongogo MCP server configured (Docker)[/green]")
    console.print(f"[dim]Config: {config_path}[/dim]")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Restart Claude Code to pick up the new configuration")
    console.print("2. Ensure your project has .pongogo/instructions/ directory")
