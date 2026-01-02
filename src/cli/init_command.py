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


def detect_knowledge_folders(cwd: Path) -> tuple[Path | None, Path | None]:
    """Detect existing wiki and docs folders in the project.

    Returns:
        Tuple of (wiki_path, docs_path) - each is None if not found.
    """
    wiki_path = None
    docs_path = None

    for name in WIKI_FOLDER_NAMES:
        candidate = cwd / name
        if candidate.is_dir():
            wiki_path = candidate
            break

    for name in DOCS_FOLDER_NAMES:
        candidate = cwd / name
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
                "  1. Check directory permissions: [cyan]ls -la $(pwd)[/cyan]"
            )
            console.print(
                "  2. On SELinux systems (Fedora/RHEL), try: [cyan]sudo chcon -Rt svirt_sandbox_file_t $(pwd)[/cyan]"
            )
            console.print("  3. Run with sudo: [cyan]sudo pongogo init[/cyan]")
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
                "  1. Check directory permissions: [cyan]ls -la $(pwd)[/cyan]"
            )
            console.print(
                "  2. On SELinux systems (Fedora/RHEL), try: [cyan]sudo chcon -Rt svirt_sandbox_file_t $(pwd)[/cyan]"
            )
            console.print("  3. Run with sudo: [cyan]sudo pongogo init[/cyan]")
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
            console.print(
                f"[yellow]Overwriting existing {PONGOGO_DIR}/ directory...[/yellow]"
            )
            import shutil

            shutil.rmtree(pongogo_dir)

    # Detect existing knowledge folders BEFORE showing welcome
    wiki_path, docs_path = detect_knowledge_folders(cwd)
    missing_folders = []
    if wiki_path is None:
        missing_folders.append("wiki/")
    if docs_path is None:
        missing_folders.append("docs/")

    # Build welcome message based on what exists
    welcome_lines = [
        "[bold blue]Pongogo[/bold blue] - AI agent knowledge routing\n",
        "This will create:",
        "  [cyan].pongogo/[/cyan]",
        "    - config.yaml (configuration)",
        "    - instructions/ (seeded instruction files)",
    ]

    if missing_folders:
        welcome_lines.append("")
        welcome_lines.append(
            "[yellow]Pongogo uses wiki/ and docs/ folders to store knowledge.[/yellow]"
        )
        welcome_lines.append("Missing folders that will be created:")
        for folder in missing_folders:
            welcome_lines.append(f"  [cyan]{folder}[/cyan]")

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
        if not typer.confirm("Continue?", default=True):
            console.print("[yellow]Installation cancelled.[/yellow]")
            raise typer.Exit(0)

    # Create wiki/docs folders if missing
    created_wiki, created_docs = create_knowledge_folders(cwd, wiki_path, docs_path)

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

    console.print(f"  [green]Seeded[/green] {files_copied} instruction files")
    console.print(
        "  [dim]Covers: engineering, project management, agentic workflows,[/dim]"
    )
    console.print(
        "  [dim]architecture, quality, security, testing, DevOps, and more.[/dim]"
    )
    console.print(
        "  [dim]These instructions evolve and adapt organically through usage.[/dim]"
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

    # Get repo name from current directory
    repo_name = cwd.name

    # Build success message with created folders and their purposes
    created_lines = [f"[green]Pongogo is now initialized in {repo_name}![/green]\n"]

    created_lines.append(f"Created: {PONGOGO_DIR}/")
    created_lines.append(
        f"  - {CONFIG_FILE} [dim](auto-configured, no edits needed)[/dim]"
    )
    created_lines.append(f"  - {INSTRUCTIONS_DIR}/ ({files_copied} files)")

    if created_wiki or created_docs:
        created_lines.append("")
        if created_wiki:
            created_lines.append(
                "  - [cyan]wiki/[/cyan] - Knowledge repository for institutional learnings"
            )
        if created_docs:
            created_lines.append(
                "  - [cyan]docs/[/cyan] - Information to help developers and agents "
                "work effectively"
            )

    created_lines.append("")
    created_lines.append(
        "[dim]Next:[/dim] Restart Claude Code and run [cyan]/mcp[/cyan] to verify "
        "Pongogo is connected."
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
