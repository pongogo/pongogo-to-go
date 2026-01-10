"""The pongogo init command implementation."""

import json
import os
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel


# Version check import (lazy to avoid import issues)
def _check_for_updates_cli(console: Console):
    """Check for updates and return message if available.

    Args:
        console: Rich console for spinner display

    Returns:
        Update message string if update available, None otherwise
    """
    # Skip version check if running from installer (we just installed latest)
    if os.environ.get("PONGOGO_FROM_INSTALLER"):
        return None

    try:
        from mcp_server.upgrade import check_for_updates

        with console.status("[dim]Checking for updates...[/dim]", spinner="dots"):
            result = check_for_updates()

        if result.update_available:
            return (
                f"\n[yellow]Update available:[/yellow] {result.current_version} → {result.latest_version}\n"
                f"Run: [#5a9ae8]{result.upgrade_command}[/#5a9ae8]"
            )
    except Exception:
        pass  # Silently skip if version check fails
    return None


def get_git_root(cwd: Path) -> Path | None:
    """Find the root of the git repository.

    Returns:
        Path to git root, or None if not in a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


from .config import generate_config, write_config
from .instructions import (
    copy_instructions,
    copy_manifest,
    copy_slash_commands,
    get_enabled_categories,
    get_package_instructions_dir,
    load_manifest,
)


# Import discovery system (lazy import to avoid circular dependencies)
def get_discovery_system():
    """Lazy import of DiscoverySystem to avoid circular imports."""
    import sys
    from pathlib import Path

    # Add mcp_server to path if needed
    mcp_server_path = Path(__file__).parent.parent / "mcp_server"
    if str(mcp_server_path) not in sys.path:
        sys.path.insert(0, str(mcp_server_path))
    from discovery_system import DiscoverySystem

    return DiscoverySystem


console = Console()

PONGOGO_DIR = ".pongogo"
CONFIG_FILE = "config.yaml"
INSTRUCTIONS_DIR = "instructions"

# Common wiki/docs folder names to detect
WIKI_FOLDER_NAMES = ["wiki", "Wiki", ".wiki"]
DOCS_FOLDER_NAMES = ["docs", "Docs", "documentation", "Documentation"]


def detect_knowledge_folders(
    cwd: Path, git_root: Path | None = None
) -> tuple[Path | None, Path | None]:
    """Detect existing wiki and docs folders in the project.

    Searches both cwd and git root (if different) to find existing folders.
    This prevents creating duplicate wiki/docs when running from a subdirectory.

    Args:
        cwd: Current working directory
        git_root: Git repository root (if in a git repo)

    Returns:
        Tuple of (wiki_path, docs_path) - each is None if not found.
    """
    wiki_path = None
    docs_path = None

    # Search locations: cwd first, then git root if different
    search_locations = [cwd]
    if git_root and git_root != cwd:
        search_locations.append(git_root)

    for location in search_locations:
        if wiki_path is None:
            for name in WIKI_FOLDER_NAMES:
                candidate = location / name
                if candidate.is_dir():
                    wiki_path = candidate
                    break

        if docs_path is None:
            for name in DOCS_FOLDER_NAMES:
                candidate = location / name
                if candidate.is_dir():
                    docs_path = candidate
                    break

    return wiki_path, docs_path


def create_knowledge_folders(
    cwd: Path,
    wiki_path: Path | None,
    docs_path: Path | None,
) -> tuple[Path | None, Path | None]:
    """Create wiki/docs folders if missing.

    These folders are needed for Pongogo to work effectively - just create them
    automatically rather than asking the user.

    Returns:
        Tuple of (created_wiki_path, created_docs_path)

    Raises:
        PermissionError: If unable to create folders (with helpful message)
    """
    created_wiki = None
    created_docs = None

    # Create wiki if missing
    if wiki_path is None:
        created_wiki = cwd / "wiki"
        try:
            created_wiki.mkdir(exist_ok=True)
        except PermissionError:
            console.print(
                "\n[red]Error:[/red] Permission denied creating wiki/ folder.",
                style="bold",
            )
            console.print(
                "\n[yellow]This is likely a Docker volume permission issue.[/yellow]"
            )
            console.print("\nPossible fixes:")
            console.print(
                "  1. Check directory permissions: [#5a9ae8]ls -la $(pwd)[/#5a9ae8]"
            )
            console.print(
                "  2. On SELinux systems (Fedora/RHEL), try: [#5a9ae8]sudo chcon -Rt svirt_sandbox_file_t $(pwd)[/#5a9ae8]"
            )
            console.print("  3. Run with sudo: [#5a9ae8]sudo pongogo init[/#5a9ae8]")
            console.print(
                "\nFor more help, see: https://github.com/pongogo/pongogo-to-go/issues"
            )
            raise
        console.print("  [green]Created[/green] wiki/")

        # Create a starter file
        readme = created_wiki / "Home.md"
        if not readme.exists():
            readme.write_text(
                "# Project Wiki\n\n"
                "This folder is for strategic documentation:\n\n"
                "- **Architecture decisions** - Why things are built the way they are\n"
                "- **Strategic context** - High-level project direction\n"
                "- **Onboarding guides** - Help new contributors get started\n"
            )

    # Create docs if missing
    if docs_path is None:
        created_docs = cwd / "docs"
        try:
            created_docs.mkdir(exist_ok=True)
        except PermissionError:
            console.print(
                "\n[red]Error:[/red] Permission denied creating docs/ folder.",
                style="bold",
            )
            console.print(
                "\n[yellow]This is likely a Docker volume permission issue.[/yellow]"
            )
            console.print("\nPossible fixes:")
            console.print(
                "  1. Check directory permissions: [#5a9ae8]ls -la $(pwd)[/#5a9ae8]"
            )
            console.print(
                "  2. On SELinux systems (Fedora/RHEL), try: [#5a9ae8]sudo chcon -Rt svirt_sandbox_file_t $(pwd)[/#5a9ae8]"
            )
            console.print("  3. Run with sudo: [#5a9ae8]sudo pongogo init[/#5a9ae8]")
            console.print(
                "\nFor more help, see: https://github.com/pongogo/pongogo-to-go/issues"
            )
            raise
        console.print("  [green]Created[/green] docs/")

        # Create a starter README
        readme = created_docs / "README.md"
        if not readme.exists():
            readme.write_text(
                "# Documentation\n\n"
                "This folder is for technical documentation:\n\n"
                "- **API references** - How to use project APIs\n"
                "- **Setup guides** - Installation and configuration\n"
                "- **Architecture docs** - Technical design documents\n"
            )

    return created_wiki, created_docs


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
    Files are created at the git repository root (if in a repo) or current directory.
    """
    cwd = Path.cwd()

    # Find git root first - all files should be created at repo root, not cwd
    git_root = get_git_root(cwd)
    project_root = git_root if git_root else cwd

    # Inform user if running from subdirectory
    if git_root and git_root != cwd:
        console.print(
            f"[dim]Running from subdirectory, will create files at repo root: {git_root}[/dim]\n"
        )

    pongogo_dir = project_root / PONGOGO_DIR

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
            console.print(
                f"[yellow]Overwriting existing {PONGOGO_DIR}/ directory...[/yellow]"
            )
            import shutil

            shutil.rmtree(pongogo_dir)

    # Detect existing knowledge folders BEFORE showing welcome
    # Check both cwd and git root to avoid creating duplicates when in subdirectory
    wiki_path, docs_path = detect_knowledge_folders(project_root, git_root)
    missing_folders = []
    if wiki_path is None:
        missing_folders.append("wiki/")
    if docs_path is None:
        missing_folders.append("docs/")

    # Build welcome message based on what exists
    welcome_lines = [
        "[bold color(208)]Pongogo[/bold color(208)] - AI agent knowledge routing\n",
        "This will create:",
        "  [#5a9ae8].pongogo/[/#5a9ae8]",
        "    - config.yaml [dim](auto-configured, no edits needed)[/dim]",
        "    - instructions/ [dim](seeded instruction files)[/dim]",
    ]

    if missing_folders:
        welcome_lines.append("")
        welcome_lines.append(
            "[yellow]Pongogo uses wiki/ and docs/ folders to store knowledge.[/yellow]"
        )
        welcome_lines.append("Missing folders that will be created:")
        for folder in missing_folders:
            welcome_lines.append(f"  [#5a9ae8]{folder}[/#5a9ae8]")

    # Show welcome message
    console.print(
        Panel(
            "\n".join(welcome_lines),
            title="Initializing Pongogo",
            border_style="blue",
        )
    )

    # Interactive mode: confirm before proceeding
    if not no_interactive:
        response = (
            console.input("\nContinue? [#5a9ae8][Y/n]:[/#5a9ae8] ").strip().lower()
        )
        if response and response not in ("y", "yes"):
            console.print("[yellow]Installation cancelled.[/yellow]")
            raise typer.Exit(0)

    # Create wiki/docs folders if missing
    created_wiki, created_docs = create_knowledge_folders(
        project_root, wiki_path, docs_path
    )

    # Track created folders for config
    final_wiki = created_wiki or wiki_path
    final_docs = created_docs or docs_path

    # Generate configuration with detected/created paths
    console.print("\n[bold]Creating configuration...[/bold]")
    config = generate_config(
        minimal=minimal,
        wiki_path=f"{final_wiki.name}/" if final_wiki else None,
        docs_path=f"{final_docs.name}/" if final_docs else None,
    )

    config_path = pongogo_dir / CONFIG_FILE
    write_config(config_path, config)
    console.print(f"  [green]Created[/green] {PONGOGO_DIR}/{CONFIG_FILE}")

    # Create .gitignore to exclude local database (contains routing history)
    gitignore_path = pongogo_dir / ".gitignore"
    gitignore_content = """# Pongogo local state (not version controlled)
# Unified database with routing events, observations, artifacts
pongogo.db
pongogo.db-wal
pongogo.db-shm
"""
    gitignore_path.write_text(gitignore_content)
    console.print(f"  [green]Created[/green] {PONGOGO_DIR}/.gitignore")

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

    # Core instructions (10) are bundled separately, always available
    core_count = 10
    total_count = files_copied + core_count
    console.print(
        f"  [green]Seeded[/green] {total_count} instruction files "
        f"[dim]({files_copied} seeded + {core_count} core)[/dim]"
    )
    console.print(
        "  [dim]Covers: engineering, project management, agentic workflows,[/dim]"
    )
    console.print(
        "  [dim]architecture, quality, security, testing, DevOps, and more.[/dim]"
    )
    console.print(
        "  [dim]These instructions evolve and adapt organically through usage.[/dim]"
    )

    # Copy slash commands to .claude/commands/
    console.print("\n[bold]Installing slash commands...[/bold]")
    claude_commands_dir = project_root / ".claude" / "commands"
    commands_copied = copy_slash_commands(claude_commands_dir)
    if commands_copied > 0:
        console.print(f"  [green]Installed[/green] {commands_copied} slash commands")
        console.print(
            "  Use [#5a9ae8]/pongogo-status[/#5a9ae8], [#5a9ae8]/pongogo-retro[/#5a9ae8], [#5a9ae8]/pongogo-log[/#5a9ae8], and more."
        )
    else:
        console.print("  [yellow]No slash commands found in package[/yellow]")

    # Configure UserPromptSubmit hook for automatic routing
    # This enables automatic context injection on every user message
    console.print("\n[bold]Configuring automatic routing hook...[/bold]")
    claude_settings_path = project_root / ".claude" / "settings.local.json"
    claude_settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Use HOST path for Docker volume mount
    host_project_dir = os.environ.get("HOST_PROJECT_DIR")
    if host_project_dir:
        hook_pongogo_path = f"{host_project_dir}/.pongogo"
    else:
        hook_pongogo_path = str(pongogo_dir.resolve())

    # Hook configuration - runs pongogo-route on each user message
    # The hook receives user message via stdin and outputs context via stdout
    hook_config = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"docker run -i --rm -v {hook_pongogo_path}:/project/.pongogo:ro pongogo.azurecr.io/pongogo:stable pongogo-route",
                        }
                    ]
                }
            ]
        }
    }

    # Write or merge hook config
    if claude_settings_path.exists():
        try:
            existing = json.loads(claude_settings_path.read_text())
            # Merge hooks, preserving other settings
            existing.setdefault("hooks", {})
            existing["hooks"]["UserPromptSubmit"] = hook_config["hooks"][
                "UserPromptSubmit"
            ]
            claude_settings_path.write_text(json.dumps(existing, indent=2) + "\n")
            console.print("  [green]Updated[/green] .claude/settings.local.json")
        except (json.JSONDecodeError, KeyError):
            claude_settings_path.write_text(json.dumps(hook_config, indent=2) + "\n")
            console.print("  [green]Created[/green] .claude/settings.local.json")
    else:
        claude_settings_path.write_text(json.dumps(hook_config, indent=2) + "\n")
        console.print("  [green]Created[/green] .claude/settings.local.json")
    console.print(
        "  [dim]Routing runs automatically on each message - no tool calls needed[/dim]"
    )

    # Scan repository for existing knowledge patterns (silently skip if nothing found)
    try:
        DiscoverySystem = get_discovery_system()
        ds = DiscoverySystem(cwd)
        scan_result = ds.scan_repository()
        # Only show discovery section if we found something interesting
        if scan_result and scan_result.total_discoveries > 0:
            console.print("\n[bold]Discovered repository knowledge:[/bold]")
            discovery_summary = ds.format_scan_summary(scan_result)
            console.print(discovery_summary)
    except Exception:
        pass  # Silently skip - discovery is optional enhancement

    # Create Claude Code MCP config for this project
    # Official location is .mcp.json at project root (not .claude/mcp.json)
    console.print("\n[bold]Configuring Claude Code MCP server...[/bold]")
    mcp_config_path = project_root / ".mcp.json"

    # Use HOST path for Docker volume mount (not container path)
    # When running in Docker, HOST_PROJECT_DIR contains the actual host path
    # When running natively, fall back to resolved path
    host_project_dir = os.environ.get("HOST_PROJECT_DIR")
    if host_project_dir:
        pongogo_abs_path = f"{host_project_dir}/.pongogo"
    else:
        pongogo_abs_path = str(pongogo_dir.resolve())
    mcp_config = {
        "mcpServers": {
            "pongogo-knowledge": {
                "command": "docker",
                "args": [
                    "run",
                    "-i",
                    "--rm",
                    "-v",
                    f"{pongogo_abs_path}:/project/.pongogo:ro",
                    "pongogo.azurecr.io/pongogo:stable",
                ],
            }
        }
    }

    # Write or merge MCP config
    if mcp_config_path.exists():
        try:
            existing = json.loads(mcp_config_path.read_text())
            existing.setdefault("mcpServers", {})
            existing["mcpServers"]["pongogo-knowledge"] = mcp_config["mcpServers"][
                "pongogo-knowledge"
            ]
            mcp_config_path.write_text(json.dumps(existing, indent=2) + "\n")
            console.print("  [green]Updated[/green] .mcp.json")
        except (json.JSONDecodeError, KeyError):
            mcp_config_path.write_text(json.dumps(mcp_config, indent=2) + "\n")
            console.print("  [green]Created[/green] .mcp.json")
    else:
        mcp_config_path.write_text(json.dumps(mcp_config, indent=2) + "\n")
        console.print("  [green]Created[/green] .mcp.json")

    # Get repo name from current directory
    repo_name = project_root.name

    # Build success message with created folders and their purposes
    created_lines = [f"[green]Pongogo is now initialized in {repo_name}![/green]\n"]

    created_lines.append(f"Created: {PONGOGO_DIR}/")
    created_lines.append(
        f"  - {CONFIG_FILE} [dim](auto-configured, no edits needed)[/dim]"
    )
    created_lines.append(
        f"  - {INSTRUCTIONS_DIR}/ [dim]({total_count} instructions: {files_copied} seeded + {core_count} core)[/dim]"
    )
    created_lines.append("  - .gitignore [dim](excludes local database)[/dim]")
    created_lines.append("")
    created_lines.append(
        "Created: .mcp.json [dim](MCP server config for Claude Code)[/dim]"
    )
    created_lines.append("")
    created_lines.append(
        "Created: .claude/settings.local.json [dim](automatic routing hook)[/dim]"
    )

    if commands_copied > 0:
        created_lines.append("")
        created_lines.append(
            f"Created: .claude/commands/ ({commands_copied} slash commands)"
        )

    if created_wiki or created_docs:
        created_lines.append("")
        if created_wiki:
            created_lines.append(
                "  - [#5a9ae8]wiki/[/#5a9ae8] - Knowledge repository for institutional learnings"
            )
        if created_docs:
            created_lines.append(
                "  - [#5a9ae8]docs/[/#5a9ae8] - Information to help developers and agents "
                "work effectively"
            )

    created_lines.append("")
    created_lines.append(
        "[dim]Next:[/dim] Restart Claude Code. When prompted, allow the "
        "[#5a9ae8]pongogo-knowledge[/#5a9ae8] MCP server."
    )
    created_lines.append(
        "[dim]      Run [#5a9ae8]/pongogo-getting-started[/#5a9ae8] for an interactive guide.[/dim]"
    )
    created_lines.append("")
    created_lines.append(
        "[dim]Tip:[/dim]  Run [#5a9ae8]/pongogo-upgrade[/#5a9ae8] periodically to stay up to date."
    )
    created_lines.append("")
    created_lines.append("[dim]Learn more:[/dim] https://pongogo.com")

    # Success message
    console.print(
        Panel(
            "\n".join(created_lines),
            title="Ready",
            border_style="green",
        )
    )

    # Check for updates (non-blocking, fails silently)
    # Skipped if PONGOGO_FROM_INSTALLER is set (install already has latest)
    update_msg = _check_for_updates_cli(console)
    if update_msg:
        console.print(update_msg)
