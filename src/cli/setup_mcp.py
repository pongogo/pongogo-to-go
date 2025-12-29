"""Setup MCP server integration with Claude Code."""

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

console = Console()


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
    """Generate MCP server configuration for Claude Code."""
    # Detect whether to use Docker or direct Python
    use_docker = has_docker()

    if use_docker:
        # Docker-based configuration
        config = {
            "command": "docker",
            "args": [
                "run",
                "-i",
                "--rm",
                "-v", "${workspaceFolder}/.pongogo:/project/.pongogo:ro",
                "ghcr.io/pongogo/pongogo-server:latest"
            ]
        }
    else:
        # Direct Python configuration (pip install)
        config = {
            "command": "pongogo-server",
            "args": [],
            "env": {
                "PONGOGO_KNOWLEDGE_PATH": "${workspaceFolder}/.pongogo/instructions"
            }
        }

    return config


def load_claude_config(path: Path) -> dict:
    """Load existing Claude Code configuration or return default."""
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except json.JSONDecodeError:
            console.print("[yellow]Warning: Could not parse existing config, starting fresh[/yellow]")
    return {}


def backup_config(path: Path) -> Optional[Path]:
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

    Automatically detects Docker availability and configures the appropriate
    connection method (Docker container or direct Python).
    """
    config_path = get_claude_config_path()
    mcp_config = get_mcp_config()
    use_docker = has_docker()

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
        console.print(f"Method: {'Docker' if use_docker else 'Direct Python'}\n")
        console.print("[bold]Configuration to add:[/bold]")
        console.print_json(json.dumps({"mcpServers": {"pongogo-knowledge": mcp_config}}))
        return

    # Create backup
    backup_path = backup_config(config_path)
    if backup_path:
        console.print(f"[dim]Backup created: {backup_path}[/dim]")

    # Write merged config
    with open(config_path, "w") as f:
        json.dump(merged_config, f, indent=2)

    # Success message
    method = "Docker" if use_docker else "Direct Python"
    console.print(f"[green]Pongogo MCP server configured ({method})[/green]")
    console.print(f"[dim]Config: {config_path}[/dim]")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Restart Claude Code to pick up the new configuration")
    console.print("2. Ensure your project has .pongogo/instructions/ directory")
